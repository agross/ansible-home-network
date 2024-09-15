CREATE ROLE IF NOT EXISTS fin_user;

GRANT fin_user TO finance@'%';
SET DEFAULT ROLE fin_user FOR finance@'%';
