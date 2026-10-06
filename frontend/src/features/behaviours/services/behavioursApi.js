export async function fetchBehaviours() {
    // Simulamos un pequeño delay de red para ver el estado de carga
    await new Promise((resolve) => setTimeout(resolve, 300));

    // Datos mock para que se luzca el frontend en el navegador
    return [
        {
            id: 1,
            name: 'Ofensivo',
            description: 'Juego de ataque rápido, presión alta',
            isDefault: true
        },
        {
            id: 2,
            name: 'Defensivo',
            description: 'Bloque bajo compacto, orden táctico defensivo y priorización de la solidez atrás.',
            isDefault: false
        },
        {
            id: 3,
            name: 'Equilibrado',
            description: 'Transiciones controladas, posesión segura y flexibilidad según el desarrollo del partido.',
            isDefault: false
        }
    ];
}
