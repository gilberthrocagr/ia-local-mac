'use strict';

// Agrupa los pedidos por estado: cuántos hay y cuánto suman.
function resumenPorEstado(pedidos) {
  const resumen = {};
  for (const p of pedidos) {
    if (!resumen[p.estado]) {
      resumen[p.estado] = { cantidad: 0, total: 0 };
    }
    resumen[p.estado].cantidad++;
    resumen[p.estado].total = p.total;
  }
  return resumen;
}

module.exports = { resumenPorEstado };
