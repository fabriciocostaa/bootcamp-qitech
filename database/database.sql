CREATE TABLE client_status(
    id		                        SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO client_status (enumerator) VALUES
('pending'),
('approved'),
('rejected');

CREATE TABLE client(
    id                              SERIAL PRIMARY KEY,
    client_key                      CHAR(36) NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES client_status(id),
    name                            VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    document_number                 CHAR(14) NOT NULL,
    password_hash                   VARCHAR(255) NOT NULL,
    birthdate                       DATE NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(client_key),
    UNIQUE(document_number),
    UNIQUE(email)
);

CREATE TABLE account_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO account_status (enumerator) VALUES
('active'),
('blocked'),
('closed');

CREATE TABLE account(
    id                              SERIAL PRIMARY KEY,
    account_key                     CHAR(36) NOT NULL,
    balance                         BIGINT NOT NULL DEFAULT(0) CHECK (balance >= 0),
    client_id                       INTEGER NOT NULL REFERENCES client(id),
    status_id                       INTEGER NOT NULL REFERENCES account_status(id),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(account_key)
);

CREATE TABLE account_status_event(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    status_id                       INTEGER NOT NULL REFERENCES account_status(id),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE client_status_event(
    id                              SERIAL PRIMARY KEY,
    client_id                       INTEGER NOT NULL REFERENCES client(id),
    status_id                       INTEGER NOT NULL REFERENCES client_status(id),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE transaction_type(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    UNIQUE(enumerator)
);

INSERT INTO transaction_type (enumerator) VALUES
('deposit'),
('withdraw'),
('transfer_in'),
('transfer_out');

CREATE TABLE account_transaction(
    id                              SERIAL PRIMARY KEY,
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    type_id                         INTEGER NOT NULL REFERENCES transaction_type(id),
    amount                          BIGINT NOT NULL CHECK (amount > 0),
    tax                             BIGINT NOT NULL CHECK (tax >= 0),
    created_at                      TIMESTAMP NOT NULL DEFAULT NOW(),
    related_transaction_id          INTEGER REFERENCES account_transaction(id)
);

CREATE TABLE idempotency_key(
    id                              SERIAL PRIMARY KEY,
    idempotency_key                 VARCHAR(255) NOT NULL,
    endpoint                        VARCHAR(255) NOT NULL,
    request_hash                    VARCHAR(64) NOT NULL,
    response_body                   JSONB NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(idempotency_key, endpoint)
);

CREATE TABLE operator(
    id                              SERIAL PRIMARY KEY,
    operator_key                    CHAR(36) NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    document_number                 CHAR(14) NOT NULL,
    password_hash                   VARCHAR(255) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(operator_key),
    UNIQUE(email)
);