"""Unit tests for Order FSM."""
import pytest
from src.database.models import OrderState
from src.fsm.order_fsm import OrderFSM, OrderFSMError


class TestOrderFSM:
    """Tests for Order FSM transitions."""
    
    def test_can_transition_draft_to_preview(self):
        """Test transition from DRAFT to PREVIEW."""
        assert OrderFSM.can_transition(OrderState.DRAFT, OrderState.PREVIEW) is True
    
    def test_can_transition_preview_to_confirmed(self):
        """Test transition from PREVIEW to CONFIRMED."""
        assert OrderFSM.can_transition(OrderState.PREVIEW, OrderState.CONFIRMED) is True
    
    def test_can_transition_preview_to_draft(self):
        """Test transition from PREVIEW back to DRAFT."""
        assert OrderFSM.can_transition(OrderState.PREVIEW, OrderState.DRAFT) is True
    
    def test_cannot_transition_draft_to_confirmed(self):
        """Test that DRAFT cannot transition directly to CONFIRMED."""
        assert OrderFSM.can_transition(OrderState.DRAFT, OrderState.CONFIRMED) is False
    
    def test_cannot_transition_from_final_states(self):
        """Test that final states cannot transition."""
        assert OrderFSM.can_transition(OrderState.CLOSED, OrderState.ACTIVE) is False
        assert OrderFSM.can_transition(OrderState.CANCELLED, OrderState.ACTIVE) is False
    
    def test_can_edit_states(self):
        """Test states that allow editing."""
        assert OrderFSM.can_edit(OrderState.DRAFT) is True
        assert OrderFSM.can_edit(OrderState.PREVIEW) is True
        assert OrderFSM.can_edit(OrderState.ACTIVE) is True
        assert OrderFSM.can_edit(OrderState.CLOSED) is False
        assert OrderFSM.can_edit(OrderState.CANCELLED) is False
    
    def test_can_cancel_states(self):
        """Test states that allow cancellation."""
        assert OrderFSM.can_cancel(OrderState.DRAFT) is True
        assert OrderFSM.can_cancel(OrderState.ACTIVE) is True
        assert OrderFSM.can_cancel(OrderState.CLOSED) is False
        assert OrderFSM.can_cancel(OrderState.CANCELLED) is False
    
    def test_can_assign_driver_states(self):
        """Test states that allow driver assignment."""
        assert OrderFSM.can_assign_driver(OrderState.ACTIVE) is True
        assert OrderFSM.can_assign_driver(OrderState.DRAFT) is False
        assert OrderFSM.can_assign_driver(OrderState.ASSIGNED) is False
    
    def test_can_close_states(self):
        """Test states that allow closing."""
        assert OrderFSM.can_close(OrderState.ASSIGNED) is True
        assert OrderFSM.can_close(OrderState.ACTIVE) is False
        assert OrderFSM.can_close(OrderState.CLOSED) is False
    
    def test_is_final_state(self):
        """Test final state detection."""
        assert OrderFSM.is_final_state(OrderState.CLOSED) is True
        assert OrderFSM.is_final_state(OrderState.CANCELLED) is True
        assert OrderFSM.is_final_state(OrderState.ACTIVE) is False


@pytest.mark.asyncio
class TestOrderFSMTransitions:
    """Integration tests for FSM transitions."""
    
    async def test_transition_draft_to_preview(self, db_session, sample_order):
        """Test transitioning order from DRAFT to PREVIEW."""
        order = await OrderFSM.transition(
            session=db_session,
            order_id=sample_order.id,
            new_state=OrderState.PREVIEW,
            changed_by=sample_order.dispatcher_id,
            change_reason="Test transition"
        )
        
        assert order.state == OrderState.PREVIEW
        
        # Check history
        history = await OrderFSM.get_order_history(db_session, sample_order.id)
        assert len(history) > 0
        assert history[-1].new_state == OrderState.PREVIEW
    
    async def test_transition_invalid_raises_error(self, db_session, sample_order):
        """Test that invalid transition raises error."""
        with pytest.raises(OrderFSMError):
            await OrderFSM.transition(
                session=db_session,
                order_id=sample_order.id,
                new_state=OrderState.CONFIRMED,  # Cannot go directly from DRAFT
                changed_by=sample_order.dispatcher_id
            )
    
    async def test_get_order_history(self, db_session, sample_order):
        """Test getting order history."""
        # Make a transition
        await OrderFSM.transition(
            session=db_session,
            order_id=sample_order.id,
            new_state=OrderState.PREVIEW,
            changed_by=sample_order.dispatcher_id
        )
        
        history = await OrderFSM.get_order_history(db_session, sample_order.id)
        assert len(history) >= 1
        assert history[0].order_id == sample_order.id

