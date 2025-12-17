"""Tests for Response Service."""
import pytest
from src.database.models import ResponseType
from src.services.response_service import ResponseService


class TestResponseService:
    """Tests for Response Service."""
    
    def test_parse_response_ya(self):
        """Test parsing 'я' response."""
        response_type = ResponseService.parse_response("я")
        assert response_type == ResponseType.YA
        
        response_type2 = ResponseService.parse_response("Я готов")
        assert response_type2 == ResponseType.YA
        
        response_type3 = ResponseService.parse_response("готов я")
        assert response_type3 == ResponseType.YA
    
    def test_parse_response_reply(self):
        """Test parsing reply response."""
        response_type = ResponseService.parse_response("Готов", is_reply=True)
        assert response_type == ResponseType.REPLY
    
    def test_parse_response_none(self):
        """Test parsing non-response."""
        response_type = ResponseService.parse_response("Просто сообщение")
        assert response_type is None
    
    @pytest.mark.asyncio
    async def test_save_response(self, db_session, sample_order):
        """Test saving driver response."""
        from src.database.models import Group
        
        # Create a group
        group = Group(
            dispatcher_id=sample_order.dispatcher_id,
            telegram_group_id=-1001234567890,
            title="Test Group"
        )
        db_session.add(group)
        await db_session.commit()
        await db_session.refresh(group)
        
        response = await ResponseService.save_response(
            session=db_session,
            order_id=sample_order.id,
            group_id=group.id,
            driver_telegram_id=111222333,
            driver_username="test_driver",
            driver_name="Test Driver",
            driver_phone="+1234567890",
            response_text="я",
            response_type=ResponseType.YA,
            message_id=12345
        )
        
        assert response is not None
        assert response.order_id == sample_order.id
        assert response.driver_telegram_id == 111222333
        assert response.response_type == ResponseType.YA
    
    @pytest.mark.asyncio
    async def test_get_responses(self, db_session, sample_order):
        """Test getting responses for order."""
        from src.database.models import Group, DriverResponse
        
        # Create group and responses
        group = Group(
            dispatcher_id=sample_order.dispatcher_id,
            telegram_group_id=-1001234567890,
            title="Test Group"
        )
        db_session.add(group)
        await db_session.commit()
        await db_session.refresh(group)
        
        # Create responses
        for i in range(3):
            response = DriverResponse(
                order_id=sample_order.id,
                group_id=group.id,
                driver_telegram_id=111222333 + i,
                driver_name=f"Driver {i}",
                response_text="я",
                response_type=ResponseType.YA,
                message_id=12345 + i
            )
            db_session.add(response)
        await db_session.commit()
        
        responses = await ResponseService.get_responses(
            session=db_session,
            order_id=sample_order.id
        )
        
        assert len(responses) == 3
    
    @pytest.mark.asyncio
    async def test_get_unique_drivers(self, db_session, sample_order):
        """Test getting unique drivers."""
        from src.database.models import Group, DriverResponse
        
        group = Group(
            dispatcher_id=sample_order.dispatcher_id,
            telegram_group_id=-1001234567890,
            title="Test Group"
        )
        db_session.add(group)
        await db_session.commit()
        await db_session.refresh(group)
        
        # Create responses from same driver
        for _ in range(3):
            response = DriverResponse(
                order_id=sample_order.id,
                group_id=group.id,
                driver_telegram_id=111222333,
                driver_name="Same Driver",
                response_text="я",
                response_type=ResponseType.YA,
                message_id=12345
            )
            db_session.add(response)
        
        # Create response from different driver
        response2 = DriverResponse(
            order_id=sample_order.id,
            group_id=group.id,
            driver_telegram_id=444555666,
            driver_name="Different Driver",
            response_text="я",
            response_type=ResponseType.YA,
            message_id=12346
        )
        db_session.add(response2)
        await db_session.commit()
        
        unique_drivers = await ResponseService.get_unique_drivers(
            session=db_session,
            order_id=sample_order.id
        )
        
        assert len(unique_drivers) == 2
        assert 111222333 in unique_drivers
        assert 444555666 in unique_drivers

