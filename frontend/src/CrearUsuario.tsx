import React, { useState } from 'react';

export default function CrearUsuario() {
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rol, setRol] = useState('operador');
  const [loading, setLoading] = useState(false);
  const [mensaje, setMensaje] = useState('');

  const handleCrearUsuario = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMensaje('');

    try {
      // AQUÍ VA TU LÓGICA REAL DE CONEXIÓN A SUPABASE O TU API
      // Ejemplo si usas fetch hacia tu backend:
      /*
      const response = await fetch('/api/crear-usuario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, rol }),
      });
      
      if (!response.ok) throw new Error('Falló la creación');
      */

      // 👇 Simulamos la llamada a la red temporalmente para que veas que funciona la UI
      await new Promise((resolve) => setTimeout(resolve, 1500));

      setMensaje('✅ Usuario creado exitosamente.');
      setEmail('');
      setPassword('');
      
      // Opcional: Ocultar el formulario después de un rato
      setTimeout(() => setMostrarFormulario(false), 2000);
    } catch (error) {
      setMensaje('❌ Error al crear el usuario.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ margin: '20px 0', padding: '15px', border: '1px solid #e0e0e0', borderRadius: '8px', maxWidth: '400px' }}>
      {!mostrarFormulario ? (
        <button 
          onClick={() => setMostrarFormulario(true)}
          style={{ padding: '10px 15px', backgroundColor: '#0070f3', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' }}
        >
          + Crear Nuevo Usuario
        </button>
      ) : (
        <form onSubmit={handleCrearUsuario} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <h3>Registrar Usuario</h3>
          
          <input 
            type="email" 
            placeholder="Correo electrónico" 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
          />
          
          <input 
            type="password" 
            placeholder="Contraseña" 
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
          />

          <select 
            value={rol} 
            onChange={(e) => setRol(e.target.value)}
            style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
          >
            <option value="operador">Operador / Obrera</option>
            <option value="tecnico">Técnico</option>
            <option value="contador">Contador</option>
          </select>

          <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
            <button 
              type="submit" 
              disabled={loading}
              style={{ flex: 1, padding: '10px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '5px', cursor: loading ? 'not-allowed' : 'pointer' }}
            >
              {loading ? 'Creando...' : 'Confirmar'}
            </button>
            <button 
              type="button" 
              onClick={() => setMostrarFormulario(false)}
              style={{ padding: '10px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
            >
              Cancelar
            </button>
          </div>
          
          {mensaje && <p style={{ fontSize: '14px', marginTop: '10px', fontWeight: 'bold' }}>{mensaje}</p>}
        </form>
      )}
    </div>
  );
}