-- fntxt2sql executes the following statement as the finance user:
-- GRANT SELECT, UPDATE ... TO fin_user;
-- finance has GRANT ALL, but this does not allow giving other users/roles
-- additional grants. The following statement enables that permission.
GRANT GRANT OPTION ON finance.* TO 'finance'@'%';
