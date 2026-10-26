import { MEDIA_V } from './manifest'

/** every file under /media carries its content hash (#251, #hd): /media/* is cached immutably, so a new file needs a new URL */
export const mediaUrl = (file: string) => `/media/${file}${MEDIA_V[file] ? `?v=${MEDIA_V[file]}` : ''}`
