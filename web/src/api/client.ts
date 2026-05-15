function detailToMessage(detail: unknown) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'msg' in item) return String(item.msg)
        return ''
      })
      .filter(Boolean)
    return messages.join('；')
  }
  return ''
}

async function responseErrorMessage(response: Response) {
  try {
    const body = (await response.json()) as { detail?: unknown }
    return detailToMessage(body.detail) || `请求失败：${response.status}`
  } catch {
    return `请求失败：${response.status}`
  }
}

async function responseJson<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    throw new Error(`请求返回了非 JSON 内容：${response.url || 'unknown'}`)
  }
  return response.json() as Promise<T>
}

function createApiClient() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return {
    async get<T>(path: string): Promise<T> {
      const response = await fetch(`${baseUrl}${path}`)
      if (!response.ok) {
        throw new Error(await responseErrorMessage(response))
      }
      return responseJson<T>(response)
    },
    async post<T>(path: string, body?: unknown): Promise<T> {
      const response = await fetch(`${baseUrl}${path}`, {
        body: body === undefined ? undefined : JSON.stringify(body),
        headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error(await responseErrorMessage(response))
      }
      return responseJson<T>(response)
    },
  }
}

const api = createApiClient()

export { api, createApiClient, detailToMessage, responseErrorMessage, responseJson }
export type ApiClient = ReturnType<typeof createApiClient>
