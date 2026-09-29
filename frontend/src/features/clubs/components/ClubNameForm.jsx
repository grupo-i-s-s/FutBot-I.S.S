import { useEffect, useId, useRef, useState } from 'react'
import { Check, LoaderCircle, Pencil } from 'lucide-react'
import { Button } from '../../../components/ui/button.jsx'

export default function ClubNameForm({
  name, isSaving, isSavingName, error, hasSaved, onSave, onReload, onClearFeedback,
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [draftName, setDraftName] = useState(name)
  const [validationError, setValidationError] = useState('')
  const inputRef = useRef(null)
  const editButtonRef = useRef(null)
  const wasEditing = useRef(false)
  const inputId = useId()
  const normalizedName = draftName.trim()
  // Python cuenta caracteres Unicode, no las unidades UTF-16 de String.length.
  const nameLength = Array.from(normalizedName).length
  const fieldError = validationError || error?.fields?.name || ''

  useEffect(() => {
    if (isEditing) inputRef.current?.focus()
    else if (wasEditing.current) editButtonRef.current?.focus()
    wasEditing.current = isEditing
  }, [isEditing])

  function handleEdit() {
    setDraftName(name)
    setValidationError('')
    onClearFeedback()
    setIsEditing(true)
  }

  function handleCancel() {
    setIsEditing(false)
    setDraftName(name)
    setValidationError('')
    onClearFeedback()
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (isSaving) return
    if (nameLength === 0 || nameLength > 50) {
      setValidationError(nameLength === 0
        ? 'Ingresá un nombre para tu club.'
        : 'El nombre no puede superar los 50 caracteres.')
      inputRef.current?.focus()
      return
    }
    if (normalizedName === name) return
    setValidationError('')
    const hasSucceeded = await onSave(normalizedName)
    if (hasSucceeded) setIsEditing(false)
  }

  return (
    <div className="mt-5">
      {isEditing ? (
        <form onSubmit={handleSubmit} noValidate className="max-w-xl space-y-3">
          <label htmlFor={inputId} className="block text-sm font-semibold">Nombre del club</label>
          <input
            ref={inputRef}
            id={inputId}
            name="name"
            type="text"
            autoComplete="off"
            required
            value={draftName}
            disabled={isSaving}
            aria-invalid={!!fieldError}
            aria-describedby={`${inputId}-help${fieldError ? ` ${inputId}-error` : ''}`}
            onChange={(event) => {
              setDraftName(event.target.value)
              setValidationError('')
              onClearFeedback()
            }}
            className="block w-full min-w-0 rounded-lg border border-frame bg-white px-3 py-2 text-base focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand disabled:opacity-60 aria-invalid:border-red-700"
          />
          <p id={`${inputId}-help`} className="text-sm text-muted-foreground">
            Entre 1 y 50 caracteres. Se quitarán los espacios al principio y al final. ({nameLength}/50)
          </p>
          {fieldError && <p id={`${inputId}-error`} role="alert" className="text-sm text-red-900">{fieldError}</p>}
          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={isSaving || normalizedName === name} size="lg">Guardar nombre</Button>
            <Button type="button" onClick={handleCancel} disabled={isSaving} variant="outline" size="lg">Cancelar</Button>
          </div>
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
              <div role="alert">
                <p className="font-semibold">No pudimos confirmar el cambio de nombre.</p>
                <p className="mt-1">{error.message}</p>
                <p className="mt-2">Conservamos lo que escribiste. Podés reintentar o consultar el nombre actual.</p>
              </div>
              <Button type="button" onClick={onReload} disabled={isSaving} variant="outline" className="mt-3">Volver a consultar</Button>
            </div>
          )}
        </form>
      ) : (
        <Button ref={editButtonRef} onClick={handleEdit} disabled={isSaving} variant="outline" size="lg">
          <Pencil className="size-4" aria-hidden="true" />Cambiar nombre
        </Button>
      )}
      <p role="status" className="mt-2 flex items-center gap-2 text-sm text-brand">
        {isSavingName ? <><LoaderCircle className="size-4 motion-safe:animate-spin" aria-hidden="true" />Guardando nombre…</>
          : hasSaved ? <><Check className="size-4" aria-hidden="true" />Nombre guardado.</> : null}
      </p>
    </div>
  )
}
