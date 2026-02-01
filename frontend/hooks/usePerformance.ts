'use client'

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'

/**
 * useDebounce - Debounce a value change
 * Useful for search inputs to prevent excessive API calls
 * 
 * @example
 * const [searchTerm, setSearchTerm] = useState('')
 * const debouncedSearch = useDebounce(searchTerm, 300)
 * 
 * useEffect(() => {
 *   // Only runs 300ms after user stops typing
 *   fetchResults(debouncedSearch)
 * }, [debouncedSearch])
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(timer)
    }
  }, [value, delay])

  return debouncedValue
}

/**
 * useDebounceCallback - Debounce a callback function
 * 
 * @example
 * const debouncedSearch = useDebounceCallback(
 *   (query) => searchAPI(query),
 *   300
 * )
 */
export function useDebounceCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void {
  const timeoutRef = useRef<NodeJS.Timeout>()

  return useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }

      timeoutRef.current = setTimeout(() => {
        callback(...args)
      }, delay)
    },
    [callback, delay]
  )
}

/**
 * useThrottle - Throttle a callback function
 * Ensures the function is called at most once per specified delay
 * 
 * @example
 * const throttledScroll = useThrottle((e) => {
 *   handleScroll(e)
 * }, 100)
 */
export function useThrottle<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): (...args: Parameters<T>) => void {
  const lastCallRef = useRef<number>(0)
  const timeoutRef = useRef<NodeJS.Timeout>()

  return useCallback(
    (...args: Parameters<T>) => {
      const now = Date.now()
      const timeSinceLastCall = now - lastCallRef.current

      if (timeSinceLastCall >= delay) {
        lastCallRef.current = now
        callback(...args)
      } else {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current)
        }
        timeoutRef.current = setTimeout(() => {
          lastCallRef.current = Date.now()
          callback(...args)
        }, delay - timeSinceLastCall)
      }
    },
    [callback, delay]
  )
}

/**
 * useMemoized - Memoize expensive calculations with cache size limit
 * 
 * @example
 * const fibonacci = useMemoized(
 *   (n) => n <= 1 ? n : fib(n-1) + fib(n-2),
 *   { maxSize: 100 }
 * )
 */
export function useMemoized<T extends (...args: any[]) => any>(
  fn: T,
  options: { maxSize?: number } = {}
): T {
  const { maxSize = 100 } = options
  const cacheRef = useRef<Map<string, ReturnType<T>>>(new Map())

  return useCallback(
    (...args: Parameters<T>): ReturnType<T> => {
      const key = JSON.stringify(args)
      
      if (cacheRef.current.has(key)) {
        // Move to end (LRU)
        const value = cacheRef.current.get(key)!
        cacheRef.current.delete(key)
        cacheRef.current.set(key, value)
        return value
      }

      const result = fn(...args)

      // Evict oldest if at capacity
      if (cacheRef.current.size >= maxSize) {
        const firstKey = cacheRef.current.keys().next().value
        cacheRef.current.delete(firstKey)
      }

      cacheRef.current.set(key, result)
      return result
    },
    [fn, maxSize]
  ) as T
}

/**
 * useOptimizedQuery - Optimized data fetching with caching and deduplication
 * 
 * @example
 * const { data, isLoading, error, refetch } = useOptimizedQuery(
 *   ['users', page],
 *   () => fetchUsers(page),
 *   { staleTime: 5 * 60 * 1000 }
 * )
 */
interface QueryOptions {
  staleTime?: number
  cacheTime?: number
  enabled?: boolean
  retry?: number | boolean
  retryDelay?: number
}

interface QueryState<T> {
  data: T | undefined
  isLoading: boolean
  isFetching: boolean
  error: Error | null
}

const queryCache = new Map<string, {
  data: any
  timestamp: number
  promise: Promise<any> | null
}>()

export function useOptimizedQuery<T>(
  key: string[],
  queryFn: () => Promise<T>,
  options: QueryOptions = {}
): QueryState<T> & { refetch: () => Promise<void> } {
  const {
    staleTime = 5 * 60 * 1000, // 5 minutes
    enabled = true,
    retry = 3,
    retryDelay = 1000,
  } = options

  const cacheKey = key.join('-')
  const [state, setState] = useState<QueryState<T>>({
    data: undefined,
    isLoading: enabled,
    isFetching: false,
    error: null,
  })

  const executeQuery = useCallback(async (isBackground = false) => {
    if (!isBackground) {
      setState(prev => ({ ...prev, isLoading: true, error: null }))
    } else {
      setState(prev => ({ ...prev, isFetching: true }))
    }

    try {
      // Check cache
      const cached = queryCache.get(cacheKey)
      const now = Date.now()
      
      if (cached && now - cached.timestamp < staleTime) {
        setState(prev => ({
          ...prev,
          data: cached.data,
          isLoading: false,
          isFetching: false,
        }))
        return
      }

      // Deduplicate in-flight requests
      if (cached?.promise) {
        const data = await cached.promise
        setState(prev => ({
          ...prev,
          data,
          isLoading: false,
          isFetching: false,
        }))
        return
      }

      // Execute with retry
      const executeWithRetry = async (attempt = 0): Promise<T> => {
        try {
          return await queryFn()
        } catch (error) {
          const maxRetries = typeof retry === 'number' ? retry : retry ? 3 : 0
          if (attempt < maxRetries) {
            await new Promise(resolve => setTimeout(resolve, retryDelay * (attempt + 1)))
            return executeWithRetry(attempt + 1)
          }
          throw error
        }
      }

      const promise = executeWithRetry()
      queryCache.set(cacheKey, {
        data: cached?.data,
        timestamp: cached?.timestamp || 0,
        promise,
      })

      const data = await promise
      
      queryCache.set(cacheKey, {
        data,
        timestamp: Date.now(),
        promise: null,
      })

      setState(prev => ({
        ...prev,
        data,
        isLoading: false,
        isFetching: false,
      }))
    } catch (error) {
      queryCache.set(cacheKey, {
        data: undefined,
        timestamp: 0,
        promise: null,
      })
      
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error : new Error(String(error)),
        isLoading: false,
        isFetching: false,
      }))
    }
  }, [cacheKey, queryFn, staleTime, retry, retryDelay])

  useEffect(() => {
    if (enabled) {
      executeQuery()
    }
  }, [enabled, executeQuery])

  const refetch = useCallback(() => executeQuery(true), [executeQuery])

  return {
    ...state,
    refetch,
  }
}

/**
 * useIntersectionObserver - Lazy load elements when they enter viewport
 * 
 * @example
 * const { ref, inView } = useIntersectionObserver({ threshold: 0.1 })
 * 
 * <div ref={ref}>
 *   {inView && <HeavyComponent />}
 * </div>
 */
interface IntersectionOptions {
  threshold?: number
  rootMargin?: string
  triggerOnce?: boolean
}

export function useIntersectionObserver<T extends HTMLElement = HTMLDivElement>(
  options: IntersectionOptions = {}
) {
  const { threshold = 0, rootMargin = '0px', triggerOnce = false } = options
  const [inView, setInView] = useState(false)
  const [hasTriggered, setHasTriggered] = useState(false)
  const ref = useRef<T>(null)

  useEffect(() => {
    const element = ref.current
    if (!element) return

    if (triggerOnce && hasTriggered) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true)
          if (triggerOnce) {
            setHasTriggered(true)
            observer.unobserve(element)
          }
        } else if (!triggerOnce) {
          setInView(false)
        }
      },
      { threshold, rootMargin }
    )

    observer.observe(element)

    return () => observer.disconnect()
  }, [threshold, rootMargin, triggerOnce, hasTriggered])

  return { ref, inView, hasTriggered }
}

/**
 * useRenderCount - Debug hook to track component re-renders
 * Only active in development mode
 * 
 * @example
 * useRenderCount('MyComponent')
 */
export function useRenderCount(componentName: string) {
  const renderCount = useRef(0)

  if (process.env.NODE_ENV === 'development') {
    renderCount.current++
    console.log(`${componentName} rendered ${renderCount.current} times`)
  }
}

/**
 * useWhyDidYouUpdate - Debug hook to track prop changes causing re-renders
 * Only active in development mode
 * 
 * @example
 * useWhyDidYouUpdate('MyComponent', props)
 */
export function useWhyDidYouUpdate<T>(componentName: string, props: T) {
  const prevProps = useRef<T>()

  useEffect(() => {
    if (process.env.NODE_ENV === 'development' && prevProps.current) {
      const allKeys = Object.keys({ ...prevProps.current, ...props })
      const changedProps = allKeys.reduce((obj, key) => {
        if ((prevProps.current as any)[key] !== (props as any)[key]) {
          return {
            ...obj,
            [key]: {
              from: (prevProps.current as any)[key],
              to: (props as any)[key],
            },
          }
        }
        return obj
      }, {})

      if (Object.keys(changedProps).length > 0) {
        console.log('[why-did-you-update]', componentName, changedProps)
      }
    }

    prevProps.current = props
  })
}
