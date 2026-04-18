CREATE TABLE zbook (
    zbookid TEXT NOT NULL,
    zrawlastaccesstime INTEGER NOT NULL
);

INSERT INTO zbook (zbookid, zrawlastaccesstime) VALUES
    ('EB000000001', 100),
    ('EB000000003', 300),
    ('EB000000002', 200);
