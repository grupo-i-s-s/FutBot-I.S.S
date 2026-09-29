import { useEffect, useRef, useState } from 'react'
import { getMyClub, updateClubAvailability } from '../api.js'

export function useMyClub() {
  const [club, setClub] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [saveError, setSaveError] = useState(null)
  const [isSaving, setIsSaving] = useState(false)
  const [hasSaved, setHasSaved] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const saveController = useRef(null)

  useEffect(() => {
    const controller = new AbortController()
    setIsLoading(true)
    setLoadError(null)
    setSaveError(null)
    setHasSaved(false)

    getMyClub({ signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setClub(data)
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setClub(null)
          setLoadError(error)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [attempt])

  useEffect(() => () => saveController.current?.abort(), [])

  async function toggleAvailability() {
    if (!club || isLoading || saveController.current) return
    const controller = new AbortController()
    saveController.current = controller
    setIsSaving(true)
    setSaveError(null)
    setHasSaved(false)

    try {
      const updatedClub = await updateClubAvailability(!club.friendlyAvailable, {
        signal: controller.signal,
      })
      if (!controller.signal.aborted) {
        setClub(updatedClub)
        setHasSaved(true)
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        if (error.status === 401 || error.code === 'ACCOUNT_INCOMPLETE') {
          setClub(null)
          setLoadError(error)
        } else {
          setSaveError(error)
        }
      }
    } finally {
      if (!controller.signal.aborted) setIsSaving(false)
      if (saveController.current === controller) saveController.current = null
    }
  }

  function reload() {
    if (!saveController.current) setAttempt((value) => value + 1)
  }

  return { club, isLoading, loadError, saveError, isSaving, hasSaved, reload, toggleAvailability }
}
