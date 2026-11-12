'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { resumenPorEstado } = require('./pedidos');

test('suma los totales de cada estado', () => {
  const r = resumenPorEstado([
    { estado: 'entregado', total: 10 },
    { estado: 'entregado', total: 5 },
    { estado: 'en_camino', total: 7 },
  ]);
  assert.deepEqual(r, {
    entregado: { cantidad: 2, total: 15 },
    en_camino: { cantidad: 1, total: 7 },
  });
});

test('redondea los totales a 2 decimales', () => {
  const r = resumenPorEstado([
    { estado: 'entregado', total: 0.1 },
    { estado: 'entregado', total: 0.2 },
  ]);
  assert.equal(r.entregado.total, 0.3);
});

test('los pedidos cancelados no cuentan', () => {
  const r = resumenPorEstado([
    { estado: 'cancelado', total: 99 },
    { estado: 'entregado', total: 4.5 },
  ]);
  assert.deepEqual(r, { entregado: { cantidad: 1, total: 4.5 } });
});

test('lista vacía da un resumen vacío', () => {
  assert.deepEqual(resumenPorEstado([]), {});
});
