-- Catálogo inicial del prototipo. No carga proyectos ficticios ni históricos.
-- Este archivo se ejecuta automáticamente solo al inicializar un volumen vacío.
USE tesis_lip;

CREATE TABLE projects (
    project_id VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    name VARCHAR(255) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (project_id),
    CONSTRAINT chk_projects_enabled CHECK (enabled IN (0, 1))
) ENGINE=InnoDB;

CREATE TABLE gateways (
    gateway_id VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    project_id VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    name VARCHAR(255) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (gateway_id),
    KEY idx_gateways_project (project_id),
    CONSTRAINT fk_gateways_project FOREIGN KEY (project_id)
        REFERENCES projects(project_id) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT chk_gateways_enabled CHECK (enabled IN (0, 1))
) ENGINE=InnoDB;
