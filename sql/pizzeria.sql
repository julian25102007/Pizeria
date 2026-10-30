-- =====================================================
-- Sistema de pedidos de pizzería (sin envíos)
-- Base de datos MySQL 8.x
-- =====================================================

DROP DATABASE IF EXISTS pizzeria;
CREATE DATABASE pizzeria CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pizzeria;

-- -----------------------------------------------------
-- Usuarios del personal (el cliente NO tiene cuenta)
-- -----------------------------------------------------
CREATE TABLE usuarios (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    usuario       VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol           ENUM('administrador', 'recepcionista', 'cocinero') NOT NULL,
    activo        BOOLEAN NOT NULL DEFAULT TRUE
);

-- -----------------------------------------------------
-- Menú: pizzas y bebidas
-- -----------------------------------------------------
CREATE TABLE productos (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(80)  NOT NULL UNIQUE,
    descripcion VARCHAR(255),
    tipo        ENUM('pizza', 'bebida') NOT NULL DEFAULT 'pizza',
    precio      DECIMAL(8,2) NOT NULL CHECK (precio > 0),
    imagen_url  VARCHAR(255),
    activo      BOOLEAN NOT NULL DEFAULT TRUE
);

-- Lista fija de ingredientes que el cliente puede agregar
CREATE TABLE ingredientes (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(60)  NOT NULL UNIQUE,
    precio_extra DECIMAL(8,2) NOT NULL DEFAULT 0 CHECK (precio_extra >= 0),
    activo       BOOLEAN NOT NULL DEFAULT TRUE
);

-- Ingredientes base de cada pizza (receta original)
CREATE TABLE producto_ingredientes (
    producto_id    INT NOT NULL,
    ingrediente_id INT NOT NULL,
    PRIMARY KEY (producto_id, ingrediente_id),
    FOREIGN KEY (producto_id)    REFERENCES productos(id)    ON DELETE CASCADE,
    FOREIGN KEY (ingrediente_id) REFERENCES ingredientes(id) ON DELETE CASCADE
);

-- -----------------------------------------------------
-- Pedidos
-- -----------------------------------------------------
CREATE TABLE pedidos (
    id             INT AUTO_INCREMENT PRIMARY KEY,   -- también es el número de pedido
    nombre_cliente VARCHAR(80) NOT NULL,
    estado         ENUM('pendiente', 'listo', 'entregado') NOT NULL DEFAULT 'pendiente',
    total          DECIMAL(10,2) NOT NULL,
    fecha_creacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_listo    DATETIME NULL,
    fecha_entrega  DATETIME NULL,
    entregado_por  INT NULL,
    pagado         BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_pago     DATETIME NULL,
    FOREIGN KEY (entregado_por) REFERENCES usuarios(id),
    INDEX idx_pedidos_estado (estado),
    INDEX idx_pedidos_fecha (fecha_creacion)
);

-- Cada pizza personalizada es una fila (cantidad = 1); las bebidas pueden llevar cantidad > 1
CREATE TABLE pedido_items (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id       INT NOT NULL,
    producto_id     INT NOT NULL,
    cantidad        INT NOT NULL DEFAULT 1 CHECK (cantidad > 0),
    precio_unitario DECIMAL(8,2) NOT NULL,           -- precio base + extras al momento del pedido
    estado_cocina   ENUM('pendiente', 'lista') NOT NULL DEFAULT 'pendiente',
    FOREIGN KEY (pedido_id)   REFERENCES pedidos(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    INDEX idx_items_estado (estado_cocina)
);

-- Solo guarda los CAMBIOS hechos a la receta base
CREATE TABLE pedido_item_ingredientes (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    item_id        INT NOT NULL,
    ingrediente_id INT NOT NULL,
    accion         ENUM('quitado', 'agregado') NOT NULL,
    precio_extra   DECIMAL(8,2) NOT NULL DEFAULT 0,  -- 0 si fue quitado
    UNIQUE (item_id, ingrediente_id),
    FOREIGN KEY (item_id)        REFERENCES pedido_items(id) ON DELETE CASCADE,
    FOREIGN KEY (ingrediente_id) REFERENCES ingredientes(id)
);

-- -----------------------------------------------------
-- Historial de cambios de precio (administrador)
-- -----------------------------------------------------
CREATE TABLE historial_precios (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    tipo            ENUM('producto', 'ingrediente') NOT NULL,
    referencia_id   INT NOT NULL,                    -- id del producto o del ingrediente
    precio_anterior DECIMAL(8,2) NOT NULL,
    precio_nuevo    DECIMAL(8,2) NOT NULL,
    usuario_id      INT NOT NULL,
    fecha           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- =====================================================
-- DATOS PRECARGADOS
-- =====================================================

-- Contraseñas de prueba (bcrypt): admin123 / recepcion123 / cocina123
INSERT INTO usuarios (nombre, usuario, password_hash, rol) VALUES
('Administrador', 'admin',     '$2b$10$PC0MEYwRxQGNWbIOezi6zeI9IwzYhTBkljdwSM4MsjLOaNwYJpX/S', 'administrador'),
('Recepcionista', 'recepcion', '$2b$10$lc8tHSsRlUS2DVsBVi7dxeg4A9Ym8N6W8x5mj9mlNNLOBcYwWw2xO', 'recepcionista'),
('Cocinero',      'cocina',    '$2b$10$GPxYe/3Yb5r4SNrcUUQi0ud/QjlFEYOlsSx0U0iIXeRcp809LPM5a', 'cocinero');

INSERT INTO ingredientes (id, nombre, precio_extra) VALUES
(1,  'Salsa de tomate',   0.00),
(2,  'Queso mozzarella',  15.00),
(3,  'Pepperoni',         20.00),
(4,  'Jamón',             15.00),
(5,  'Piña',              10.00),
(6,  'Chorizo',           20.00),
(7,  'Jalapeño',          10.00),
(8,  'Cebolla',           10.00),
(9,  'Pimiento',          10.00),
(10, 'Champiñones',       15.00),
(11, 'Aceitunas',         10.00),
(12, 'Queso cheddar',     15.00),
(13, 'Queso parmesano',   15.00),
(14, 'Queso gorgonzola',  20.00),
(15, 'Albahaca',           5.00),
(16, 'Tocino',            20.00);

INSERT INTO productos (id, nombre, descripcion, tipo, precio) VALUES
(1, 'Margarita',     'Clásica con mozzarella y albahaca fresca',          'pizza',  120.00),
(2, 'Pepperoni',     'Mozzarella y abundante pepperoni',                  'pizza',  135.00),
(3, 'Hawaiana',      'Jamón y piña sobre mozzarella',                     'pizza',  135.00),
(4, 'Mexicana',      'Chorizo, jalapeño y cebolla',                       'pizza',  145.00),
(5, 'Cuatro Quesos', 'Mozzarella, cheddar, parmesano y gorgonzola',       'pizza',  150.00),
(6, 'Vegetariana',   'Champiñones, pimiento, cebolla y aceitunas',        'pizza',  130.00),
(7, 'Refresco',      'Botella de 600 ml',                                 'bebida',  25.00),
(8, 'Agua natural',  'Botella de 600 ml',                                 'bebida',  20.00);

-- Ingredientes base de cada pizza
INSERT INTO producto_ingredientes (producto_id, ingrediente_id) VALUES
-- Margarita
(1, 1), (1, 2), (1, 15),
-- Pepperoni
(2, 1), (2, 2), (2, 3),
-- Hawaiana
(3, 1), (3, 2), (3, 4), (3, 5),
-- Mexicana
(4, 1), (4, 2), (4, 6), (4, 7), (4, 8),
-- Cuatro Quesos
(5, 1), (5, 2), (5, 12), (5, 13), (5, 14),
-- Vegetariana
(6, 1), (6, 2), (6, 10), (6, 9), (6, 8), (6, 11);
