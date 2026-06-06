import React from 'react';
// Como están en la misma carpeta, usamos './' en lugar de '../components/'
import CrearUsuario from './CrearUsuario';

export default function TecnicoView() {
  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Panel de Técnico</h1>
      <p>Bienvenido. En esta vista puedes gestionar a los usuarios del sistema.</p>
      
      {/* Aquí insertas el componente funcional para crear usuarios */}
      <CrearUsuario />

      {/* Más adelante puedes agregar aquí una tabla para listar/editar usuarios */}
      <div style={{ marginTop: '30px', padding: '15px', border: '1px solid #ccc', borderRadius: '8px' }}>
        <h3>Directorio de Usuarios</h3>
        <p style={{ color: '#666' }}>Aquí irá el listado de usuarios del sistema...</p>
      </div>
    </div>
  );
}