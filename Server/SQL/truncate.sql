DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN (
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'core'
  )
  LOOP
    EXECUTE 'TRUNCATE TABLE core.' || quote_ident(r.tablename) || ' CASCADE;';
  END LOOP;
END $$;