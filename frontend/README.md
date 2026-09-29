# Frontend de FutBot

## Pantalla Mi club — ISS-108

Disponible en `/club`, con acceso desde la pantalla de conexión `/`.
Usa `GET /api/club/me` y `PATCH /api/club/me` del backend de ISS-120,
con la cookie de sesión de Autenticación y el encabezado de escritura
`X-Futbot-Request: 1`. Implementación y pendientes de integración:
[ISS-108](../docs/iss_108_my_club.md).

La pantalla está en `src/features/clubs/MyClubPage.jsx`; recibe las rutas de los
otros módulos mediante `destinations` y la de ingreso mediante `loginHref`.
Mientras no estén integrados, los módulos se muestran como «Próximamente».
El escudo es provisional: no se interpreta el campo `avatar` hasta acordar su formato.

Guía para desarrollar la interfaz en equipo con **React, JavaScript, Vite y Tailwind CSS**.
Las convenciones de este documento son la propuesta de trabajo del proyecto;
si el equipo cambia una, debe actualizar esta guía en la misma entrega.

Para instalar y levantar el entorno completo, seguir el [README principal](../README.md).
Los comandos de Docker de esta guía se ejecutan desde la **raíz del repositorio**,
no desde `frontend/`.

## 1. Qué hace cada archivo actual

| Archivo o carpeta | Para qué sirve | Cómo se trabaja con él |
| --- | --- | --- |
| `package.json` | Declara nombre, scripts y dependencias directas del proyecto. | Actualizarlo con npm al agregar o quitar paquetes. |
| `package-lock.json` | Guarda las versiones resueltas de dependencias directas y transitivas, junto con sus datos de descarga. | Se genera con npm y se sube a Git junto con `package.json`. No editarlo a mano. |
| `Dockerfile` | Define la imagen con Node, instala dependencias y establece el comando de inicio. | Modificarlo si cambia la preparación del entorno. |
| `.dockerignore` | Excluye archivos del contexto que Docker usa para construir la imagen. | Evita copiar `node_modules`, compilaciones y configuraciones locales. No reemplaza a `.gitignore`. |
| `index.html` | Es la página de entrada de Vite; contiene el elemento donde React se monta. | Mantener aquí los metadatos generales de la página. |
| `vite.config.js` | Configura los plugins de React y Tailwind, el servidor, la detección de cambios y el proxy hacia FastAPI. | La configuración del entorno va aquí; la lógica de negocio, en `src/`. |
| `src/main.jsx` | Monta React en `#root` y carga los estilos globales. | Mantenerlo pequeño; agregar aquí los proveedores globales cuando existan. |
| `src/App.jsx` | Componente raíz. Actualmente muestra el estado de conexión. | Componer las pantallas; evitar concentrar aquí toda la aplicación. |
| `src/styles.css` | Importa Tailwind y define los colores del tema y estilos base. | Reservarlo para reglas generales y variables de diseño compartidas. |
| `node_modules/` | Paquetes instalados por npm. | Generado, no se versiona. Compose lo guarda en un volumen separado. |
| `dist/` | Archivos generados por la compilación para distribución. | Generado, no editar ni versionar. |

Una **dependencia directa** es un paquete elegido por el equipo, como React.
Una **transitiva** es un paquete que otra dependencia necesita. En `package.json`,
`dependencies` contiene bibliotecas de la aplicación y `devDependencies`, herramientas
de desarrollo o compilación, como Vite, `tailwindcss` y `@tailwindcss/vite`.
Ambas categorías se instalan en este entorno.
El frontend no usa archivos `requirements`: esos pertenecen al proyecto Python.

## 2. Convenciones de nombres y estilo

Usar **inglés en identificadores** y **español en textos de la interfaz y documentación**.
Por ejemplo, `playerName` en el código y «Nombre del jugador» en la pantalla.
Mantener el vocabulario del contrato: `player`, `club`, `league`, `match` y `behaviour`.
No alternar `behaviour` con `behavior` para la misma entidad.

| Elemento | Convención | Ejemplo |
| --- | --- | --- |
| Componentes y archivos de componentes | `PascalCase`, extensión `.jsx` | `PlayerCard.jsx`, `PlayerCard` |
| Pantallas | `PascalCase` con sufijo `Page` | `PlayerListPage.jsx` |
| Variables, funciones y props | `camelCase` | `playerName`, `loadPlayers`, `onSelect` |
| Hooks propios | Nombre `use` + `PascalCase`; archivo `.js` | `usePlayers.js`, `usePlayers()` |
| Booleanos | Nombre que exprese una condición | `isLoading`, `hasError`, `canSubmit` |
| Manejadores internos de eventos | Prefijo `handle` | `handleSubmit`, `handlePlayerSelect` |
| Props que notifican eventos al padre | Prefijo `on` | `onSubmit`, `onPlayerSelect` |
| Constantes fijas compartidas | `UPPER_SNAKE_CASE` | `POLL_INTERVAL_MS` |
| Carpetas | Minúsculas y `kebab-case` si tienen varias palabras | `players/`, `friendly-matches/` |
| Módulos sin JSX | `camelCase`, extensión `.js` | `formatDate.js`, `http.js` |
| Estilos de componente | Utilidades Tailwind en `className`; CSS Modules para excepciones | `className="rounded-lg p-4"`, `PlayerCard.module.css` |
| Pruebas futuras | Nombre del módulo + `.test.jsx` o `.test.js` | `PlayerCard.test.jsx`, `formatDate.test.js` |
| Recursos gráficos | Minúsculas y `kebab-case` | `default-avatar.svg` |

Usar `const` por defecto y `let` cuando haya reasignación; evitar `var`. No todas las
variables declaradas con `const` necesitan mayúsculas: `const playerName = ...`
es un valor de trabajo, no una constante de configuración.

Mantener el estilo de los archivos actuales: dos espacios, comillas simples en
JavaScript, comillas dobles en atributos JSX y sin punto y coma. JSON requiere
comillas dobles. Usar UTF-8 y fin de línea LF. Respetar exactamente las mayúsculas
de los imports: un nombre incorrecto puede funcionar en macOS y fallar en Linux.

Un componente principal por archivo. Usar exportación `default` para el componente
principal y exportaciones nombradas para hooks, funciones de API y utilidades.
Ordenar imports: bibliotecas externas, módulos propios y estilos. Mantener rutas
relativas mientras no exista un alias configurado; `@/` todavía no está disponible.

## 3. Estructura al agregar funcionalidades

Actualmente existen los archivos descritos en la sección 1. Este árbol es una
**estructura propuesta para crecer**: crear cada carpeta cuando tenga contenido,
sin mover la base ni crear archivos vacíos solo para completar el dibujo.

```text
src/
  main.jsx
  App.jsx
  styles.css
  api/
    http.js                      # Peticiones y errores HTTP comunes
  components/
    Button.jsx                   # Componentes compartidos por varias funciones
  features/
    players/
      PlayerListPage.jsx         # Pantalla del plantel
      api.js                     # listPlayers, createPlayer
      components/
        PlayerCard.jsx
      hooks/
        usePlayers.js
    friendly-matches/
      FriendlyMatchListPage.jsx
      api.js
  hooks/                         # Hooks realmente compartidos
  utils/
    formatDate.js                # Funciones puras, sin React ni peticiones
  assets/                        # Recursos importados por los componentes
```

Guardar lo específico dentro de su funcionalidad (`features/players/`). Moverlo a
una carpeta compartida cuando tenga varios consumidores. Los componentes compartidos
no deben importar pantallas ni depender de una funcionalidad particular. Evitar
imports entre archivos internos de distintas funcionalidades; extraer una parte
común cuando sea necesario. No crear un `utils.js` que mezcle peticiones, fechas y formularios.

Las páginas coordinan los datos y componen la pantalla. Los componentes pequeños
reciben datos y eventos por props. Los hooks encapsulan lógica con estado o efectos;
una función pura de formato no necesita convertirse en hook.
[Referencia de React sobre hooks propios](https://react.dev/learn/reusing-logic-with-custom-hooks).

## 4. Estado, componentes y estilos

- Mantener el estado cerca de donde se usa; elevarlo al padre común cuando varias
  partes lo comparten. No incorporar una biblioteca global sin una necesidad concreta.
- No mutar directamente props ni objetos o arrays guardados en estado.
- Usar IDs estables como `key` para entidades. Evitar el índice si la lista puede
  reordenarse, agregar o eliminar elementos.
- Distinguir carga, error, lista vacía y resultado. Una falla de red no equivale a
  «no hay jugadores». Permitir reintentar cuando corresponda.
- Cancelar peticiones y limpiar temporizadores al desmontar o cambiar sus parámetros;
  evitar que una respuesta antigua sobrescriba una selección reciente.
- Preferir elementos semánticos (`button`, `form`, `label`) y controles accesibles
  con teclado. Asociar las etiquetas a los campos y mostrar los errores junto al formulario.
- Para nuevos componentes, usar las utilidades de Tailwind en `className`. Reservar
  CSS Modules para estilos específicos que lo necesiten y mantener las reglas
  globales en `styles.css`, dentro de `@layer base`. Evitar reglas globales que
  sobrescriban las utilidades para resolver el diseño de una sola pantalla.

### Tailwind CSS

Está integrado **Tailwind CSS 4** mediante el plugin `@tailwindcss/vite` y la
importación `@import "tailwindcss";` en `src/styles.css`. Vite genera el CSS tanto
en desarrollo como al compilar. Esta integración no necesita `tailwind.config.js`,
configuración de PostCSS ni un comando separado para compilar estilos.
[Instalación oficial con Vite](https://tailwindcss.com/docs/installation/using-vite).

Ejemplo de JSX:

```jsx
<button className="rounded-lg bg-brand px-4 py-2 text-white hover:opacity-90 disabled:opacity-50">
  Guardar
</button>
```

Para trabajar en equipo:

- Usar primero las utilidades existentes de espaciado, tipografía y tamaño. Extraer
  un componente compartido si varias pantallas repiten la misma combinación.
- Los colores compartidos se definen con `@theme` en `src/styles.css`: actualmente
  `brand`, `canvas`, `ink` y `frame`, que permiten clases como `bg-brand`, `bg-canvas`,
  `text-ink` y `border-frame`. Agregar allí nuevos valores de diseño que se repitan.
- Escribir clases completas, incluso cuando dependen del estado. Usar un mapa como
  `statusClasses` en `App.jsx` o un ternario con cadenas completas. Evitar construir
  nombres como `bg-${color}-500`, que el detector no puede reconocer como clases completas.
- Diseñar primero para pantallas pequeñas y aplicar variantes como `sm:` o `md:`
  donde haga falta. Incluir estados de foco y controles deshabilitados.
- El CSS de la aplicación entra por `main.jsx`. Mantener esa importación para que
  Tailwind y los estilos base estén disponibles en todas las pantallas.

Para recibir esta dependencia o cambios posteriores, usar el procedimiento habitual
desde la raíz: `docker compose up --build -d --wait`. Los Dockerfiles y Compose ya
instalan los paquetes declarados; no hace falta instalar Tailwind en la computadora.

### Componentes shadcn/ui

shadcn/ui está configurado sobre Tailwind 4. La CLI usa `components.json` y el alias
`@/` apunta a `src/` mediante `jsconfig.json` y `vite.config.js`. Los componentes
se generan en JavaScript (`.jsx`), según `"tsx": false` en `components.json`.
`src/styles.css` contiene los tokens de shadcn/ui junto con los colores de FutBot.

Para agregar un componente desde `frontend/`:

```sh
npx shadcn add dialog
```

Si se trabaja con el contenedor iniciado, desde la raíz:

```sh
docker compose exec frontend npx shadcn add dialog
```

Los archivos generados quedan en `src/components/ui/` y se pueden importar, por
ejemplo, con `import { Button } from '@/components/ui/button'`. El componente
`Button` ya está incluido como ejemplo. Revisar los cambios de `styles.css` y de
dependencias cuando se agreguen otros componentes, y versionar el lockfile de npm.

## 5. Contrato con el backend

Consultar el [contrato de Sprint 2](../docs/api_sprint_2.md) antes de implementar
una pantalla. Ese documento está marcado como **propuesta**; los cambios de contrato
se coordinan entre FE y BE y se reflejan allí. No demuestra que los endpoints ya existan.

El navegador usa rutas relativas con `/api`: `/api/players` se traduce a `/players`
de FastAPI. No escribir `http://backend:8000` en un componente ni fijar `localhost:8000`.
El proxy está configurado en Vite para desarrollo; una publicación de `dist/` necesitará
su propia configuración de servidor.

Conservar los campos JSON del contrato, como `clubId`, `behaviourId` o `startDateTime`.
No renombrarlos unilateralmente. Las listas propuestas usan `{ "items": [...] }`.
La validación del formulario ayuda al usuario; el backend sigue siendo responsable
de validar reglas, permisos y propiedad de los recursos.

Al implementar el cliente HTTP común, comprobar `response.ok`, contemplar respuestas
`204` sin JSON y distinguir errores de red de errores funcionales. Para estos últimos,
usar `error.code`, mostrar `error.message` y asociar `error.fields` a los campos,
según el contrato. No decidir el comportamiento comparando mensajes en español.

Enviar fechas con zona horaria y convertirlas para mostrarlas en la zona local.
Un valor de un control `datetime-local` requiere conversión antes de enviarlo.
Coordinar autenticación y manejo de `401` en el cliente HTTP; todavía no existe una
implementación de login en esta base.

`API_PROXY_TARGET` y `VITE_USE_POLLING` son leídas por la configuración actual.
Las variables `VITE_*` pueden quedar expuestas al navegador: no colocar contraseñas
ni claves privadas allí. La configuración compartida del entorno se documenta en
el `.env.example` de la raíz.

## 6. Agregar o actualizar dependencias

Con el frontend iniciado, reemplazar `nombre-del-paquete` por el paquete elegido:

```sh
# Biblioteca usada por la aplicación
docker compose exec frontend npm install --save-exact nombre-del-paquete

# Herramienta de desarrollo
docker compose exec frontend npm install --save-dev --save-exact nombre-del-paquete

# Quitar una dependencia
docker compose exec frontend npm uninstall nombre-del-paquete
```

Versionar juntos `package.json` y `package-lock.json`. Usar npm en este proyecto;
no agregar lockfiles de Yarn o pnpm. Antes de agregar una biblioteca, revisar si
la necesidad ya está cubierta por React o por otra dependencia existente.

Compose ejecuta `npm ci` al iniciar: instala desde el lockfile y falla si este no
coincide con `package.json`. No sirve para agregar paquetes. Después de recibir
cambios de dependencias, ejecutar `docker compose up --build -d --wait`.
[Referencia de npm ci](https://docs.npmjs.com/cli/v11/commands/npm-ci/).

## 7. Comprobar el trabajo antes de compartirlo

```sh
docker compose exec frontend npm run build
docker compose logs --tail=100 frontend
```

Verificar en el navegador el flujo modificado, incluyendo error, carga, campos
inválidos y pantalla angosta cuando corresponda. Una compilación exitosa no valida
por sí sola el comportamiento de la interfaz.

Existen los scripts `dev`, `build`, `preview` y `test`. `npm test` ejecuta las pruebas
de navegador con Playwright, junto al componente (`*.test.js`). No hay `lint`
ni un formateador configurado.

Desde `frontend/`, con Node compatible instalado (ver `package.json`):

```sh
npm ci
npx playwright install chromium
npm test
npm run build
```

Para ejecutarlas dentro del contenedor Linux, desde la raíz:

```sh
docker compose exec frontend npx playwright install --with-deps chromium
docker compose exec frontend npm test
```

Playwright inicia su propio Vite en `127.0.0.1:4173`; dejar ese puerto libre.
Las pruebas de Mi club simulan las respuestas HTTP: verifican la interfaz y sus
peticiones, pero no reemplazan la prueba integrada con Autenticación y PostgreSQL.
Los fallos dejan trazas en `test-results/`, excluido de Git. Los fixtures de navegación
en `tests/fixtures/` son exclusivos de pruebas, no pantallas de otros módulos.

`preview` sirve para revisar la compilación y no reemplaza al entorno integrado
de desarrollo, cuyo proxy está en `server.proxy`.

## 8. Coordinación del equipo

1. Revisar el ticket y acordar con backend rutas, campos, errores y ejemplos antes
   de construir el formulario o la pantalla.
2. Trabajar en una rama por tarea, con nombre descriptivo en minúsculas y guiones;
   por ejemplo, `feat/<ticket>-player-list`. Reemplazar `<ticket>` por el identificador real.
3. Mantener cambios pequeños y relacionados. Evitar reformatear archivos ajenos o
   modificar el contrato sin avisar a quienes consumen la API.
4. Usar commits del tipo `feat: agregar listado de jugadores`, `fix: corregir envío
   del formulario` o `docs: explicar configuración`. Reservar `refactor:` para cambios
   de estructura sin cambio de comportamiento.
5. En la solicitud de revisión, indicar qué cambió, cómo probarlo, evidencia de UI
   y qué falta. Si se usa información simulada, identificarla explícitamente.
6. Resolver conflictos de dependencias combinando las intenciones en `package.json`
   y regenerando el lockfile con npm. No elegir una versión del lockfile a ciegas.

Guía relacionada: [convenciones del backend](../backend/README.md).
