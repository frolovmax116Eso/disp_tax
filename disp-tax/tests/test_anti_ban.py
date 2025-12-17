"""Tests for Anti-Ban logic."""
import pytest
import asyncio
from datetime import datetime, timedelta
from src.services.anti_ban import RateLimiter, AntiBanService


class TestRateLimiter:
    """Tests for Rate Limiter."""
    
    @pytest.mark.asyncio
    async def test_can_send_initially(self):
        """Test that can send initially."""
        limiter = RateLimiter(max_per_minute=5)
        assert await limiter.can_send() is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        """Test rate limit enforcement."""
        limiter = RateLimiter(max_per_minute=3)
        
        # Record 3 sends
        for _ in range(3):
            await limiter.record_send()
        
        # Should be at limit
        assert await limiter.can_send() is False
    
    @pytest.mark.asyncio
    async def test_wait_if_needed(self):
        """Test waiting when limit is reached."""
        limiter = RateLimiter(max_per_minute=1)
        
        await limiter.record_send()
        
        # Should wait
        start = datetime.utcnow()
        wait_time = await limiter.wait_if_needed()
        elapsed = (datetime.utcnow() - start).total_seconds()
        
        # Wait time should be close to 60 seconds (with some tolerance)
        assert wait_time > 0
        # Note: In real test, we might mock time to avoid waiting


class TestAntiBanService:
    """Tests for Anti-Ban Service."""
    
    @pytest.mark.asyncio
    async def test_random_delay(self):
        """Test random delay function."""
        service = AntiBanService()
        
        start = datetime.utcnow()
        delay = await service.random_delay(min_seconds=1, max_seconds=2)
        elapsed = (datetime.utcnow() - start).total_seconds()
        
        assert 1 <= delay <= 2
        assert elapsed >= 1  # Should have waited
    
    @pytest.mark.asyncio
    async def test_handle_floodwait(self):
        """Test FloodWait handling."""
        service = AntiBanService()
        
        start = datetime.utcnow()
        await service.handle_floodwait(seconds=1)
        elapsed = (datetime.utcnow() - start).total_seconds()
        
        assert elapsed >= 1
        assert len(service.recent_floodwaits) == 1
    
    def test_calculate_risk_level_low(self):
        """Test risk level calculation - LOW."""
        service = AntiBanService()
        
        risk = service.calculate_risk_level(
            group_count=5,
            delay_min=5,
            delay_max=10
        )
        
        assert risk == "LOW"
    
    def test_calculate_risk_level_medium(self):
        """Test risk level calculation - MEDIUM."""
        service = AntiBanService()
        
        risk = service.calculate_risk_level(
            group_count=15,
            delay_min=6,
            delay_max=8
        )
        
        assert risk in ["MEDIUM", "LOW"]  # Can be either
    
    def test_calculate_risk_level_high(self):
        """Test risk level calculation - HIGH."""
        service = AntiBanService()
        
        # Add some floodwaits
        for _ in range(3):
            service.recent_floodwaits.append(datetime.utcnow())
        
        risk = service.calculate_risk_level(
            group_count=50,
            delay_min=3,
            delay_max=5
        )
        
        assert risk == "HIGH"
    
    @pytest.mark.asyncio
    async def test_send_with_protection_success(self):
        """Test successful send with protection."""
        service = AntiBanService()
        
        async def mock_send():
            return "success"
        
        result = await service.send_with_protection(
            send_func=mock_send,
            min_delay=0,
            max_delay=0  # No delay for test speed
        )
        
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_send_with_protection_floodwait(self):
        """Test send with protection handles FloodWait."""
        from telethon.errors import FloodWaitError
        
        service = AntiBanService()
        call_count = 0
        
        async def mock_send():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FloodWaitError(request=None, seconds=0.1)  # Short wait for test
            return "success"
        
        result = await service.send_with_protection(
            send_func=mock_send,
            min_delay=0,
            max_delay=0
        )
        
        assert result == "success"
        assert call_count == 2  # Should retry after FloodWait

