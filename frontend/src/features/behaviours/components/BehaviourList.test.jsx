import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import BehaviourList from './BehaviourList';
import { fetchBehaviours } from '../services/behavioursApi';

// Mockeamos el servicio de API
vi.mock('../services/behavioursApi', () => ({
  fetchBehaviours: vi.fn(),
}));

describe('BehaviourList Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('muestra el estado de carga y luego renderiza la lista con nombres, descripciones, marca default y enlaces de navegación', async () => {
    const mockBehaviours = [
      { id: 1, name: 'Ofensivo', description: 'Juego de ataque rápido', isDefault: true },
      { id: 2, name: 'Defensivo', description: 'Bloque bajo compacto', isDefault: false },
    ];
    fetchBehaviours.mockResolvedValueOnce(mockBehaviours);

    render(<BehaviourList />);

    // Verificar estado de carga inicial
    expect(screen.getByText(/cargando catálogo/i)).toBeInTheDocument();

    // Esperar a que se rendericen los datos
    await waitFor(() => {
      expect(screen.getByText('Ofensivo')).toBeInTheDocument();
      expect(screen.getByText('Juego de ataque rápido')).toBeInTheDocument();
      expect(screen.getByText('Default')).toBeInTheDocument();
      expect(screen.getByText('Defensivo')).toBeInTheDocument();
    });

    // Verificar enlaces por ID de navegación al detalle
    const links = screen.getAllByText(/ver detalle/i);
    expect(links).toHaveLength(2);
    expect(links[0].getAttribute('href')).toBe('/behaviours/1');
    expect(links[1].getAttribute('href')).toBe('/behaviours/2');

    // Verificar ausencia absoluta de controles fuera de alcance (crear o eliminar)
    expect(screen.queryByText(/crear/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/eliminar/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/nuevo/i)).not.toBeInTheDocument();
  });

  it('maneja el estado de error y permite reintentar la carga', async () => {
    fetchBehaviours.mockRejectedValueOnce(new Error('Error al cargar el catálogo de comportamientos.'));

    render(<BehaviourList />);

    await waitFor(() => {
      expect(screen.getByText(/error al cargar el catálogo/i)).toBeInTheDocument();
    });

    const retryButton = screen.getByRole('button', { name: /reintentar/i });
    expect(retryButton).toBeInTheDocument();

    // Simulamos que al reintentar ahora sí responde con éxito
    fetchBehaviours.mockResolvedValueOnce([
      { id: 1, name: 'Equilibrado', description: 'Juego mixto', isDefault: false }
    ]);

    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText('Equilibrado')).toBeInTheDocument();
    });
  });

  it('muestra el estado vacío cuando la lista no tiene elementos', async () => {
    fetchBehaviours.mockResolvedValueOnce([]);

    render(<BehaviourList />);

    await waitFor(() => {
      expect(screen.getByText(/no hay comportamientos disponibles/i)).toBeInTheDocument();
    });
  });
});
