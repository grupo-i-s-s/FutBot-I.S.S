import { ArrowUpRight, Code2, LayoutGrid, Swords, Trophy, Users } from 'lucide-react'

const sections = [
  { key: 'players', title: 'Plantel', description: 'Conocé a los jugadores de tu club.', icon: Users },
  { key: 'team', title: 'Mi equipo', description: 'Prepará tu formación y alineación.', icon: LayoutGrid },
  { key: 'behaviours', title: 'Comportamientos', description: 'Explorá cómo juegan tus jugadores.', icon: Code2 },
  { key: 'leagues', title: 'Ligas', description: 'Encontrá tu próxima competencia.', icon: Trophy },
  { key: 'friendlyMatches', title: 'Amistosos', description: 'Buscá rivales y jugá un partido.', icon: Swords },
]

// El integrador provee las rutas reales cuando cada módulo esté disponible.
export default function ClubNavigation({ destinations = {} }) {
  return (
    <section aria-labelledby="club-sections-title">
      <h2 id="club-sections-title" className="text-xl font-semibold">Tu club, en juego</h2>
      <p className="mt-2 text-sm text-muted-foreground">Todo lo que necesitás para preparar tu próxima participación.</p>
      <ul className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {sections.map(({ key, title, description, icon: Icon }) => {
          const href = destinations[key]
          const content = (
            <>
              <span className="mb-5 flex items-center justify-between">
                <Icon className="size-6 text-brand" aria-hidden="true" />
                {href ? <ArrowUpRight className="size-5" aria-hidden="true" /> : (
                  <span className="rounded-full bg-canvas px-2.5 py-1 text-xs text-muted-foreground">Próximamente</span>
                )}
              </span>
              <span className="block font-semibold">{title}</span>
              <span className="mt-1 block text-sm text-muted-foreground">{description}</span>
            </>
          )
          return (
            <li key={key}>
              {href ? (
                <a href={href} className="block h-full rounded-2xl border border-frame bg-white p-5 transition-colors hover:border-brand focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand">
                  {content}
                </a>
              ) : (
                <div className="h-full rounded-2xl border border-frame bg-white/60 p-5">
                  {content}
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
