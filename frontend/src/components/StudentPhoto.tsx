import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'

// id:version -> object URL. A new photo_version is a new key, so replaced
// photos refresh while unchanged ones are fetched once per session.
const cache = new Map<string, Promise<string>>()

const loadPhoto = (id: string, version: string) => {
  const key = `${id}:${version}`
  let url = cache.get(key)
  if (!url) {
    url = api.getStudentPhoto(id, version).then((blob) => URL.createObjectURL(blob))
    url.catch(() => cache.delete(key)) // let a later render retry
    cache.set(key, url)
  }
  return url
}

interface StudentPhotoProps {
  id?: string
  name: string
  version?: string | null
  /** A local image (blob/data URL) to show instead of the saved photo. */
  src?: string | null
  size?: 'sm' | 'lg'
}

export const StudentPhoto: React.FC<StudentPhotoProps> = ({ id, name, version, src, size = 'sm' }) => {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (src || !id || !version) { setUrl(null); return }
    let alive = true
    loadPhoto(id, version).then((u) => alive && setUrl(u)).catch(() => alive && setUrl(null))
    return () => { alive = false }
  }, [id, version, src])

  const shown = src || url
  const initial = name.trim().charAt(0) || '?'
  return (
    <span className={`student-photo student-photo-${size}`}>
      {shown ? <img src={shown} alt={`រូបថត ${name}`} /> : <span aria-hidden="true">{initial}</span>}
    </span>
  )
}
