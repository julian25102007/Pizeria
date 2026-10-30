-- Ejecutar UNA sola vez sobre una base que ya tiene pedidos (Aiven).
ALTER TABLE pedidos
    ADD COLUMN pagado     BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN fecha_pago DATETIME NULL;
-- Los pedidos ya entregados se consideran cobrados
UPDATE pedidos SET pagado = TRUE, fecha_pago = fecha_entrega WHERE estado = 'entregado';
