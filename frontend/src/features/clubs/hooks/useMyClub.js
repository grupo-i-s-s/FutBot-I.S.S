import { useEffect, useRef, useState } from 'react'
import { getMyClub, updateClubAvailability, updateClubName } from '../api.js'

export function useMyClub() {
  const [club, setClub] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [saveError, setSaveError] = useState(null)
  const [savingField, setSavingField] = useState(null)
  const [hasSaved, setHasSaved] = useState(false)
  const [nameError, setNameError] = useState(null)
  const [hasNameSaved, setHasNameSaved] = useState(false)
  const [refreshError, setRefreshError] = useState(null)
  const [loadRequest, setLoadRequest] = useState({ attempt: 0, preserveClub: false })
  const saveController = useRef(null)

  useEffect(() => {
    const controller = new AbortController()
    setIsLoading(true)
    setLoadError(null)
    setSaveError(null)
    setHasSaved(false)
    setNameError(null)
    setHasNameSaved(false)
    setRefreshError(null)

    getMyClub({ signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setClub(data)
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          if (loadRequest.preserveClub && error.status !== 401 && error.code !== 'ACCOUNT_INCOMPLETE') {
            setRefreshError(error)
          } else {
            setClub(null)
            setLoadError(error)
          }
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [loadRequest])

  useEffect(() => () => saveController.current?.abort(), [])

  // Serializar escrituras evita que respuestas completas de Club se pisen.
  async function saveChanges(update, field) {
    if (!club || isLoading || saveController.current) return false
    const controller = new AbortController()
    saveController.current = controller
    setSavingField(field)
    setSaveError(null)
    setHasSaved(false)
    setNameError(null)
    setHasNameSaved(false)
    setRefreshError(null)

    try {
      const updatedClub = await update({ signal: controller.signal })
      if (!controller.signal.aborted) {
        setClub(updatedClub)
        setHasSaved(field === 'availability')
        setHasNameSaved(field === 'name')
        return true
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        if (error.status === 401 || error.code === 'ACCOUNT_INCOMPLETE') {
          setClub(null)
          setLoadError(error)
        } else if (field === 'name') {
          setNameError(error)
        } else {
          setSaveError(error)
        }
      }
    } finally {
      if (!controller.signal.aborted) setSavingField(null)
      if (saveController.current === controller) saveController.current = null
    }
    return false
  }

  function toggleAvailability() {
    return saveChanges((options) => updateClubAvailability(!club.friendlyAvailable, options), 'availability')
  }

  function saveName(name) {
    return saveChanges((options) => updateClubName(name, options), 'name')
  }

  function clearNameFeedback() {
    setNameError(null)
    setHasNameSaved(false)
  }

  function reload() {
    if (!saveController.current && !isLoading) {
      setLoadRequest((current) => ({ attempt: current.attempt + 1, preserveClub: !!club }))
    }
  }

  return {
    club, isLoading, loadError, refreshError, saveError, hasSaved, nameError, hasNameSaved,
    isSaving: savingField !== null,
    isSavingName: savingField === 'name',
    isSavingAvailability: savingField === 'availability',
    reload, toggleAvailability, saveName, clearNameFeedback,
  }
}
