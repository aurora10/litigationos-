-- D10-T01: agent tasks + actions
CREATE TABLE IF NOT EXISTS agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    instruction TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'case_manager',  -- planner routes: case_manager/evidence/timeline/research/adversarial/drafting
    status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (status IN ('QUEUED','RUNNING','WAITING_APPROVAL','COMPLETED','FAILED')),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    finished_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tasks_case ON agent_tasks(case_id);

CREATE TABLE IF NOT EXISTS agent_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES agent_tasks(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_input JSONB,
    result JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_actions_task ON agent_actions(task_id);

CREATE TABLE IF NOT EXISTS agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES agent_tasks(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,     -- reading_documents | searching_evidence | found_contradiction | preparing_draft | waiting_approval | synthesizing
    message TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_events_task ON agent_events(task_id);
