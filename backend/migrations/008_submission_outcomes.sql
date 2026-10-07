-- Preserve optional attempt outcomes as recommendation signals without changing lifecycle status.
ALTER TABLE submissions ADD COLUMN completion_state TEXT CHECK (
    completion_state IN ('solved_independently', 'hint_used', 'gave_up')
);
ALTER TABLE submissions ADD COLUMN time_taken_minutes INTEGER CHECK (
    time_taken_minutes >= 0
);
