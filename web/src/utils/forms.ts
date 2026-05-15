import type {
  MediaLibraryFormState,
  RemoteMediaLibraryFormState,
  DtlConfigFormState,
  DtlConfigResponse,
  DtlBindingFormState,
  SyncConfigFormState,
  SyncConfigResponse,
  SyncBindingFormState,
  StorageFormState,
  StorageConfigResponse,
  StorageConfigRequest,
} from '../types'

export function emptyLibraryForm(): MediaLibraryFormState {
  return { id: '', name: '', media_type: 'movie', enabled: true, connection_id: '', base_path: '/' }
}

export function emptyRemoteLibraryForm(): RemoteMediaLibraryFormState {
  return { id: '', name: '', media_type: 'movie', enabled: true, connection_id: '', base_path: '/', target_library_id: '', scan_interval_seconds: '60', stable_seconds: '120', delete_source_after_success: '', delete_empty_source_dirs: 'true' }
}

export function emptyDtlConfigForm(): DtlConfigFormState {
  return { delete_source_after_success: true, delete_empty_source_dirs: true, scan_interval_seconds: '60', stable_seconds: '120', unclassified_library_id: '' }
}

export function dtlConfigFormFromResponse(config: DtlConfigResponse): DtlConfigFormState {
  return { delete_source_after_success: config.delete_source_after_success, delete_empty_source_dirs: config.delete_empty_source_dirs, scan_interval_seconds: String(config.scan_interval_seconds), stable_seconds: String(config.stable_seconds), unclassified_library_id: config.unclassified_library_id }
}

export function dtlConfigRequestFromForm(form: DtlConfigFormState) {
  return { delete_source_after_success: form.delete_source_after_success, delete_empty_source_dirs: form.delete_empty_source_dirs, scan_interval_seconds: Number(form.scan_interval_seconds) || 60, stable_seconds: Number(form.stable_seconds) || 120, unclassified_library_id: form.unclassified_library_id.trim() }
}

export function emptySyncConfigForm(): SyncConfigFormState {
  return { delete_source_after_success: true, delete_empty_source_dirs: true, scan_interval_seconds: '60', stable_seconds: '120', unclassified_library_id: '' }
}

export function syncConfigFormFromResponse(config: SyncConfigResponse): SyncConfigFormState {
  return { delete_source_after_success: config.delete_source_after_success, delete_empty_source_dirs: config.delete_empty_source_dirs, scan_interval_seconds: String(config.scan_interval_seconds), stable_seconds: String(config.stable_seconds), unclassified_library_id: config.unclassified_library_id }
}

export function syncConfigRequestFromForm(form: SyncConfigFormState) {
  return { delete_source_after_success: form.delete_source_after_success, delete_empty_source_dirs: form.delete_empty_source_dirs, scan_interval_seconds: Number(form.scan_interval_seconds) || 60, stable_seconds: Number(form.stable_seconds) || 120, unclassified_library_id: form.unclassified_library_id.trim() }
}

export function emptySyncBindingForm(): SyncBindingFormState {
  return { id: '', name: '', enabled: true, media_type: 'movie', remote_library_id: '', local_library_id: '', delete_source_after_success: '', delete_empty_source_dirs: '' }
}

export function emptyDtlBindingForm(): DtlBindingFormState {
  return { id: '', name: '', enabled: true, media_type: 'movie', source_connection_id: '', source_path: '', target_library_id: '', delete_source_after_success: '', delete_empty_source_dirs: '' }
}

export function emptyStorageForm(): StorageFormState {
  return {
    host: '',
    port: '445',
    share: '',
    username: '',
    password: '',
    domain: '',
    base_path: '/',
    library_movies: '',
    library_tv: '',
    library_anime: '',
  }
}

export function storageFormFromConfig(config: StorageConfigResponse): StorageFormState {
  return {
    host: config.host,
    port: String(config.port || 445),
    share: config.share,
    username: config.username,
    password: '',
    domain: config.domain || '',
    base_path: config.base_path || '/',
    library_movies: config.libraries.movies || '',
    library_tv: config.libraries.tv || '',
    library_anime: config.libraries.anime || '',
  }
}

export function storageRequestFromForm(form: StorageFormState): StorageConfigRequest {
  const libraries: Record<string, string> = {}
  if (form.library_movies.trim()) libraries.movies = form.library_movies.trim()
  if (form.library_tv.trim()) libraries.tv = form.library_tv.trim()
  if (form.library_anime.trim()) libraries.anime = form.library_anime.trim()

  return {
    type: 'smb',
    host: form.host.trim(),
    port: Number(form.port) || 445,
    share: form.share.trim(),
    username: form.username.trim(),
    password: form.password ? form.password : null,
    domain: form.domain.trim(),
    base_path: form.base_path.trim() || '/',
    libraries,
  }
}
