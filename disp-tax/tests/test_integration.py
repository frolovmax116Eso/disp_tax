"""Integration tests for main workflows."""
import pytest
from src.database.models import OrderState, ResponseType
from src.services.order_service import OrderService
from src.services.response_service import ResponseService
from src.services.assignment_service import AssignmentService
from src.fsm.order_fsm import OrderFSM


@pytest.mark.asyncio
class TestOrderWorkflow:
    """End-to-end tests for order workflow."""
    
    async def test_full_order_lifecycle(self, db_session, sample_dispatcher):
        """Test complete order lifecycle from creation to closing."""
        # 1. Create order
        order = await OrderService.create_order(
            session=db_session,
            dispatcher_id=sample_dispatcher.id,
            content="Integration test order"
        )
        assert order.state == OrderState.DRAFT
        
        # 2. Preview
        preview = await OrderService.preview_order(
            session=db_session,
            order_id=order.id
        )
        assert preview["state"] == OrderState.PREVIEW.value
        
        # 3. Confirm
        order = await OrderService.confirm_order(
            session=db_session,
            order_id=order.id,
            dispatcher_id=sample_dispatcher.id
        )
        assert order.state == OrderState.CONFIRMED
        
        # 4. Transition to ACTIVE (simulating send)
        order = await OrderFSM.transition(
            session=db_session,
            order_id=order.id,
            new_state=OrderState.ACTIVE,
            changed_by=sample_dispatcher.id,
            change_reason="Order sent"
        )
        assert order.state == OrderState.ACTIVE
        
        # 5. Add driver response
        from src.database.models import Group
        
        group = Group(
            dispatcher_id=sample_dispatcher.id,
            telegram_group_id=-1001234567890,
            title="Test Group"
        )
        db_session.add(group)
        await db_session.commit()
        await db_session.refresh(group)
        
        response = await ResponseService.save_response(
            session=db_session,
            order_id=order.id,
            group_id=group.id,
            driver_telegram_id=111222333,
            driver_username="test_driver",
            driver_name="Test Driver",
            driver_phone=None,
            response_text="я",
            response_type=ResponseType.YA,
            message_id=12345
        )
        assert response is not None
        
        # 6. Assign driver
        assignment = await AssignmentService.assign_driver(
            session=db_session,
            order_id=order.id,
            driver_telegram_id=111222333,
            driver_username="test_driver",
            driver_name="Test Driver",
            assigned_by=sample_dispatcher.id
        )
        assert assignment is not None
        
        # Check order state changed to ASSIGNED
        order = await OrderService.get_order(db_session, order.id)
        assert order.state == OrderState.ASSIGNED
        
        # 7. Close order
        order = await OrderService.close_order(
            session=db_session,
            order_id=order.id,
            dispatcher_id=sample_dispatcher.id
        )
        assert order.state == OrderState.CLOSED
    
    async def test_order_edit_workflow(self, db_session, sample_order):
        """Test order editing workflow."""
        # Edit order
        new_content = "Updated order content"
        order = await OrderService.edit_order(
            session=db_session,
            order_id=sample_order.id,
            new_content=new_content,
            dispatcher_id=sample_order.dispatcher_id
        )
        
        assert order.content == new_content
        
        # Verify history
        history = await OrderFSM.get_order_history(db_session, sample_order.id)
        assert len(history) > 0
    
    async def test_order_cancel_workflow(self, db_session, sample_order):
        """Test order cancellation workflow."""
        # Cancel order
        order = await OrderService.cancel_order(
            session=db_session,
            order_id=sample_order.id,
            dispatcher_id=sample_order.dispatcher_id,
            reason="Test cancellation"
        )
        
        assert order.state == OrderState.CANCELLED
        
        # Verify cannot edit cancelled order
        with pytest.raises(Exception):  # Should raise OrderFSMError
            await OrderService.edit_order(
                session=db_session,
                order_id=sample_order.id,
                new_content="New content",
                dispatcher_id=sample_order.dispatcher_id
            )

