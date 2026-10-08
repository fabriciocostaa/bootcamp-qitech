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
('transfer_out'),
('fee_debit'),
('fee_credit');

CREATE TABLE operation_kind(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    UNIQUE(enumerator)
);

INSERT INTO operation_kind (enumerator) VALUES
('deposit'),
('withdraw'),
('transfer');

CREATE TABLE account_operation(
    id                              SERIAL PRIMARY KEY,
    operation_key                   CHAR(36) NOT NULL,
    actor_client_id                 INTEGER NOT NULL REFERENCES client(id),
    kind_id                         INTEGER NOT NULL REFERENCES operation_kind(id),
    origin_account_id               INTEGER REFERENCES account(id),
    target_account_id               INTEGER REFERENCES account(id),
    amount                          BIGINT NOT NULL CHECK (amount > 0),
    fee                             BIGINT NOT NULL DEFAULT 0,
    idempotency_key                 VARCHAR(255) NOT NULL,
    request_hash                    VARCHAR(64),
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(operation_key),
    UNIQUE(actor_client_id, idempotency_key)
);

CREATE TABLE account_transaction(
    id                              SERIAL PRIMARY KEY,
    operation_id                    INTEGER NOT NULL REFERENCES account_operation(id),
    account_id                      INTEGER NOT NULL REFERENCES account(id),
    type_id                         INTEGER NOT NULL REFERENCES transaction_type(id),
    amount                          BIGINT NOT NULL CHECK (amount > 0),
    created_at                      TIMESTAMP NOT NULL DEFAULT NOW(),
    related_transaction_id          INTEGER REFERENCES account_transaction(id)
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

CREATE TABLE credit_line(
    id                      SERIAL PRIMARY KEY,
    credit_line_key         CHAR(36) NOT NULL,
    client_id               INTEGER NOT NULL REFERENCES client(id),
    approved_limit          BIGINT NOT NULL CHECK (approved_limit >= 0),
    available_limit         BIGINT NOT NULL CHECK (available_limit >= 0),
    interest_rate           NUMERIC(5, 4) NOT NULL,
    status                  VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at              TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(credit_line_key)
);

CREATE TABLE invoice_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO invoice_status (enumerator) VALUES
('open'),
('closed'),
('paid'),
('overdue');

CREATE TABLE credit_invoice(
    id                              SERIAL PRIMARY KEY,
    invoice_key                     CHAR(36) NOT NULL,
    credit_line_id                  INTEGER NOT NULL REFERENCES credit_line(id),
    status_id                       INTEGER NOT NULL REFERENCES invoice_status(id),
    billing_cycle                   VARCHAR(7) NOT NULL,
    amount_due                      BIGINT NOT NULL DEFAULT(0) CHECK (amount_due >= 0),
    due_date                        TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(invoice_key)
);

CREATE TABLE invoice_status_event(
    id                              SERIAL PRIMARY KEY,
    invoice_id                      INTEGER NOT NULL REFERENCES credit_invoice(id),
    status_id                       INTEGER NOT NULL REFERENCES invoice_status(id),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);