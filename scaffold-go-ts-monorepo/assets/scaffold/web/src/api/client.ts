import type { ResponseEnvelope } from './generated'

export * from './generated/sdk.gen'

export class ApiError extends Error {
  readonly code: number

  constructor(code: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

type ApiEnvelope<T> = Omit<ResponseEnvelope, 'data'> & { data: T }

export async function unwrap<T>(request: PromiseLike<ApiEnvelope<T>>): Promise<T> {
  try {
    const response = await request
    if (response.code !== 0) throw new ApiError(response.code, response.msg)
    return response.data
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (isResponseEnvelope(error)) throw new ApiError(error.code, error.msg)
    if (error instanceof Error) throw new ApiError(-1, error.message)
    throw new ApiError(-1, 'API request failed')
  }
}

function isResponseEnvelope(value: unknown): value is ResponseEnvelope {
  return (
    typeof value === 'object' && value !== null &&
    'code' in value && typeof value.code === 'number' &&
    'msg' in value && typeof value.msg === 'string' && 'data' in value
  )
}
