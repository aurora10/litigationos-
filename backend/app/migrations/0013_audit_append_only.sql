-- D16: lock audit_logs to append-only. The app connects with the same DB user that
-- owns the tables, so we can't rely on role separation alone; instead we block the
-- two mutation paths at the DB level with triggers (and revoke any future bypass).
CREATE OR REPLACE FUNCTION audit_logs_no_update() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_logs is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_logs_no_update ON audit_logs;
DROP TRIGGER IF EXISTS audit_logs_no_delete ON audit_logs;
CREATE TRIGGER audit_logs_no_update BEFORE UPDATE ON audit_logs FOR EACH ROW EXECUTE FUNCTION audit_logs_no_update();
CREATE TRIGGER audit_logs_no_delete BEFORE DELETE ON audit_logs FOR EACH ROW EXECUTE FUNCTION audit_logs_no_update();
