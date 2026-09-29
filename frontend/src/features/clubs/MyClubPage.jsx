import { AlertCircle, Check, LoaderCircle, Shield, Swords } from 'lucide-react'
import { Button } from '../../components/ui/button.jsx'
import ClubNavigation from './components/ClubNavigation.jsx'
import ClubNameForm from './components/ClubNameForm.jsx'
import { useMyClub } from './hooks/useMyClub.js'

export default function MyClubPage({ destinations = {}, loginHref }) {
  const {
    club, isLoading, loadError, refreshError, saveError, isSaving, hasSaved, reload, toggleAvailability,
    nameError, hasNameSaved, isSavingName, isSavingAvailability, saveName, clearNameFeedback,
  } = useMyClub()
  const needsSession = loadError?.status === 401
  const isAccountIncomplete = loadError?.code === 'ACCOUNT_INCOMPLETE'

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="border-b border-frame bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-5 sm:px-8">
          <span className="flex items-center gap-2 text-xl font-bold"><Shield className="size-6 text-brand" aria-hidden="true" />FutBot</span>
          <span className="rounded-full bg-canvas px-4 py-2 text-sm font-medium">Mi club</span>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-8 px-5 py-8 sm:px-8 sm:py-12">
        <div>
          <p className="text-xs font-semibold tracking-widest text-brand uppercase">Tu espacio en FutBot</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">Mi club</h1>
          <p className="mt-3 text-muted-foreground">Prepará tu club para el próximo desafío.</p>
        </div>

        {isLoading && !club ? (
          <div role="status" className="flex min-h-56 items-center justify-center gap-3 rounded-2xl border border-frame bg-white p-6">
            <LoaderCircle className="size-5 motion-safe:animate-spin" aria-hidden="true" />
            Cargando tu club…
          </div>
        ) : loadError ? (
          <section className="rounded-2xl border border-frame bg-white p-6 sm:p-8">
            <div role="alert">
              <AlertCircle className="mb-4 size-7 text-brand" aria-hidden="true" />
              <h2 className="text-xl font-semibold">
                {needsSession ? 'Necesitás iniciar sesión' : isAccountIncomplete ? 'Tu cuenta todavía no tiene un club' : 'No pudimos cargar tu club'}
              </h2>
              <p className="mt-2 text-muted-foreground">
                {needsSession ? 'Iniciá sesión con tu cuenta y volvé a intentar.' : loadError.message}
              </p>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              {needsSession && loginHref && (
                <a href={loginHref} className="rounded-lg bg-brand px-4 py-2 text-sm text-white focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand">Iniciar sesión</a>
              )}
              <Button onClick={reload} variant="outline" size="lg">Volver a intentar</Button>
            </div>
          </section>
        ) : club && (
          <>
            {isLoading && <p role="status" className="text-sm text-brand">Actualizando tu club…</p>}
            {refreshError && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
                <div role="alert">
                  <p className="font-semibold">No pudimos actualizar los datos del club.</p>
                  <p className="mt-1">{refreshError.message}</p>
                  <p className="mt-2">Mostramos los últimos datos confirmados y conservamos tu borrador.</p>
                </div>
                <Button onClick={reload} disabled={isSaving || isLoading} variant="outline" className="mt-3">Volver a consultar</Button>
              </div>
            )}
            <section aria-labelledby="club-name" className="flex flex-col gap-5 rounded-2xl border border-frame bg-white p-6 sm:flex-row sm:items-start sm:p-8">
              <div role="img" aria-label="Escudo provisional del club" className="flex size-20 shrink-0 items-center justify-center rounded-2xl bg-brand text-white">
                <Shield className="size-10" aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-muted-foreground">Tu club</p>
                <h2 id="club-name" className="mt-1 text-2xl font-bold break-words sm:text-3xl">{club.name}</h2>
                <p className="mt-3 inline-flex items-center gap-2 text-sm">
                  <span aria-hidden="true" className={`size-2 rounded-full ${club.friendlyAvailable ? 'bg-brand' : 'bg-slate-400'}`} />
                  {club.friendlyAvailable ? 'Disponible para nuevos amistosos' : 'No disponible para nuevos amistosos'}
                </p>
                <ClubNameForm
                  name={club.name}
                  isSaving={isSaving || isLoading}
                  isSavingName={isSavingName}
                  error={nameError}
                  hasSaved={hasNameSaved}
                  onSave={saveName}
                  onReload={reload}
                  onClearFeedback={clearNameFeedback}
                />
              </div>
            </section>

            <section aria-labelledby="availability-title" className="rounded-2xl border border-frame bg-white p-6 sm:p-8">
              <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-start">
                <div className="max-w-xl">
                  <div className="flex items-center gap-2">
                    <Swords className="size-5 text-brand" aria-hidden="true" />
                    <h2 id="availability-title" className="text-lg font-semibold">Disponibilidad para amistosos</h2>
                  </div>
                  <p id="availability-description" className="mt-3 text-sm leading-relaxed text-muted-foreground">
                    {club.friendlyAvailable
                      ? 'Tu club está habilitado para crear o unirse a nuevos amistosos, siempre que cumpla los demás requisitos del partido.'
                      : 'Activá la disponibilidad para poder crear o unirte a nuevos amistosos. También deberás cumplir los requisitos de cada partido.'}
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={club.friendlyAvailable}
                  aria-label="Disponibilidad para amistosos"
                  aria-describedby="availability-description availability-effect"
                  disabled={isSaving || isLoading}
                  onClick={toggleAvailability}
                  className="flex shrink-0 cursor-pointer items-center gap-3 self-start rounded-lg p-2 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand disabled:cursor-wait disabled:opacity-60"
                >
                  <span className="text-sm font-medium">{club.friendlyAvailable ? 'Activada' : 'Desactivada'}</span>
                  <span aria-hidden="true" className={`flex h-7 w-12 items-center rounded-full p-1 transition-colors ${club.friendlyAvailable ? 'bg-brand' : 'bg-slate-400'}`}>
                    <span className={`size-5 rounded-full bg-white shadow-sm transition-transform ${club.friendlyAvailable ? 'translate-x-5' : 'translate-x-0'}`} />
                  </span>
                </button>
              </div>
              <p id="availability-effect" className="mt-6 border-t border-frame pt-4 text-sm text-muted-foreground">
                Este cambio solo afecta nuevas participaciones. No cancela amistosos aceptados ni modifica partidos en curso.
              </p>
              <p role="status" className="mt-3 flex min-h-6 items-center gap-2 text-sm text-brand">
                {isSavingAvailability ? <><LoaderCircle className="size-4 motion-safe:animate-spin" aria-hidden="true" />Guardando disponibilidad…</> : hasSaved ? <><Check className="size-4" aria-hidden="true" />Disponibilidad guardada.</> : null}
              </p>
              {saveError && (
                <div className="mt-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
                  <div role="alert">
                    <p className="font-semibold">No pudimos confirmar el cambio.</p>
                    <p className="mt-1">{saveError.message}</p>
                    <p className="mt-2">Mostramos el último valor confirmado. Consultá el estado actual o volvé a intentar con el interruptor.</p>
                  </div>
                  <Button onClick={reload} variant="outline" className="mt-3">Volver a consultar</Button>
                </div>
              )}
            </section>

            <ClubNavigation destinations={destinations} />
          </>
        )}
      </main>
    </div>
  )
}
