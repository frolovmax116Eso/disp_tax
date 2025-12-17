"""Unit tests for Order Service."""
import pytest
from src.database.models import OrderState
from src.services.order_service import OrderService
from src.fsm.order_fsm import OrderFSMError


@pytest.mark.asyncio
class TestOrderService:
    """Tests for Order Service."""
    
    async def test_create_order(self, db_session, sample_dispatcher):
        """Test creating a new order."""
        order = await OrderService.create_order(
            session=db_session,
            dispatcher_id=sample_dispatcher.id,
            content="Test order content for creation"
        )
        
        assert order is not None
        assert order.state == OrderState.DRAFT
        assert order.content == "Test order content for creation"
        assert order.dispatcher_id == sample_dispatcher.id
    
    def test_normalize_content(self):
        """Test content normalization."""
        content = "  Test   order   content  "
        normalized = OrderService.normalize_content(content)
        assert normalized == "Test order content"
        
        # Test with newlines
        content2 = "Test\norder\ncontent"
        normalized2 = OrderService.normalize_content(content2)
        assert "  " not in normalized2
    
    async def test_preview_order(self, db_session, sample_order):
        """Test getting order preview."""
        preview = await OrderService.preview_order(
            session=db_session,
            order_id=sample_order.id
        )
        
        assert preview is not None
        assert preview["order_id"] == sample_order.id
        assert preview["content"] == sample_order.content
        assert preview["state"] == OrderState.PREVIEW.value
    
    async def test_confirm_order(self, db_session, sample_order):
        """Test confirming an order."""
        # First transition to PREVIEW
        await OrderFSM.transition(
            session=db_session,
            order_id=sample_order.id,
            new_state=OrderState.PREVIEW,
            changed_by=sample_order.dispatcher_id
        )
        
        # Then confirm
        order = await OrderService.confirm_order(
            session=db_session,
            order_id=sample_order.id,
            dispatcher_id=sample_order.dispatcher_id
        )
        
        assert order.state == OrderState.CONFIRMED
        assert order.confirmed_at is not None
    
    async def test_edit_order(self, db_session, sample_order):
        """Test editing an order."""
        new_content = "Updated order content"
        
        order = await OrderService.edit_order(
            session=db_session,
            order_id=sample_order.id,
            new_content=new_content,
            dispatcher_id=sample_order.dispatcher_id
        )
        
        assert order.content == new_content
        assert order.normalized_content == OrderService.normalize_content(new_content)
    
    async def test_cancel_order(self, db_session, sample_order):
        """Test cancelling an order."""
        order = await OrderService.cancel_order(
            session=db_session,
            order_id=sample_order.id,
            dispatcher_id=sample_order.dispatcher_id,
            reason="Test cancellation"
        )
        
        assert order.state == OrderState.CANCELLED
        assert order.closed_at is not None
    
    async def test_close_order(self, db_session, sample_order):
        """Test closing an order."""
        # First transition to ASSIGNED
        await OrderFSM.transition(
            session=db_session,
            order_id=sample_order.id,
            new_state=OrderState.ACTIVE,
            changed_by=sample_order.dispatcher_id
        )
        await OrderFSM.transition(
            session=db_session,
            order_id=sample_order.id,
            new_state=OrderState.ASSIGNED,
            changed_by=sample_order.dispatcher_id
        )
        
        # Then close
        order = await OrderService.close_order(
            session=db_session,
            order_id=sample_order.id,
            dispatcher_id=sample_order.dispatcher_id
        )
        
        assert order.state == OrderState.CLOSED
        assert order.closed_at is not None
    
    async def test_get_order(self, db_session, sample_order):
        """Test getting order by ID."""
        order = await OrderService.get_order(
            session=db_session,
            order_id=sample_order.id
        )
        
        assert order is not None
        assert order.id == sample_order.id
    
    async def test_get_dispatcher_orders(self, db_session, sample_dispatcher):
        """Test getting dispatcher's orders."""
        # Create multiple orders
        for i in range(3):
            await OrderService.create_order(
                session=db_session,
                dispatcher_id=sample_dispatcher.id,
                content=f"Order {i}"
            )
        
        orders = await OrderService.get_dispatcher_orders(
            session=db_session,
            dispatcher_id=sample_dispatcher.id
        )
        
        assert len(orders) >= 3

