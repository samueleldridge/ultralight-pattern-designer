'use client'

import { useState, useMemo, useCallback, useRef, useEffect } from 'react'

/**
 * useVirtualList - Virtual scrolling for large datasets
 * Only renders visible items, dramatically improving performance with large lists
 * 
 * Inspired by React Virtual / TanStack Virtual
 * 
 * @example
 * const { virtualItems, totalHeight, scrollRef } = useVirtualList({
 *   items: largeArray,
 *   itemHeight: 50,
 *   overscan: 5
 * })
 * 
 * <div ref={scrollRef} style={{ height: '400px', overflow: 'auto' }}>
 *   <div style={{ height: totalHeight }}>
 *     {virtualItems.map((item) => (
 *       <div key={item.key} style={{ 
 *         height: item.height, 
 *         transform: `translateY(${item.offset}px)` 
 *       }}>
 *         {item.data}
 *       </div>
 *     ))}
 *   </div>
 * </div>
 */
interface VirtualListOptions<T> {
  items: T[]
  itemHeight: number | ((item: T, index: number) => number)
  overscan?: number
  scrollPaddingStart?: number
  scrollPaddingEnd?: number
}

interface VirtualItem<T> {
  index: number
  key: string
  data: T
  offset: number
  height: number
}

interface VirtualListResult<T> {
  virtualItems: VirtualItem<T>[]
  totalHeight: number
  scrollRef: React.RefObject<HTMLDivElement>
  scrollToIndex: (index: number, behavior?: ScrollBehavior) => void
  scrollToOffset: (offset: number, behavior?: ScrollBehavior) => void
  isScrolling: boolean
}

export function useVirtualList<T>(options: VirtualListOptions<T>): VirtualListResult<T> {
  const {
    items,
    itemHeight,
    overscan = 5,
    scrollPaddingStart = 0,
    scrollPaddingEnd = 0,
  } = options

  const scrollRef = useRef<HTMLDivElement>(null)
  const [scrollOffset, setScrollOffset] = useState(0)
  const [containerHeight, setContainerHeight] = useState(0)
  const [isScrolling, setIsScrolling] = useState(false)
  const scrollTimeoutRef = useRef<NodeJS.Timeout>()

  // Calculate heights for each item
  const measurements = useMemo(() => {
    const measurements: { height: number; offset: number }[] = []
    let totalHeight = scrollPaddingStart

    items.forEach((item, index) => {
      const height = typeof itemHeight === 'function' 
        ? itemHeight(item, index) 
        : itemHeight
      
      measurements.push({
        height,
        offset: totalHeight,
      })
      totalHeight += height
    })

    return { measurements, totalHeight: totalHeight + scrollPaddingEnd }
  }, [items, itemHeight, scrollPaddingStart, scrollPaddingEnd])

  // Calculate visible range
  const virtualItems = useMemo(() => {
    const { measurements, totalHeight } = measurementsData
    const virtualItems: VirtualItem<T>[] = []

    if (!containerHeight) return virtualItems

    // Find start index
    let startIndex = 0
    for (let i = 0; i < measurements.length; i++) {
      if (measurements[i].offset + measurements[i].height > scrollOffset) {
        startIndex = i
        break
      }
    }

    // Apply overscan to start
    startIndex = Math.max(0, startIndex - overscan)

    // Find end index
    let endIndex = startIndex
    for (let i = startIndex; i < measurements.length; i++) {
      if (measurements[i].offset > scrollOffset + containerHeight) {
        endIndex = i
        break
      }
      endIndex = i + 1
    }

    // Apply overscan to end
    endIndex = Math.min(measurements.length, endIndex + overscan)

    // Create virtual items
    for (let i = startIndex; i < endIndex; i++) {
      virtualItems.push({
        index: i,
        key: `virtual-${i}`,
        data: items[i],
        offset: measurements[i].offset,
        height: measurements[i].height,
      })
    }

    return virtualItems
  }, [measurements, scrollOffset, containerHeight, overscan, items])

  const measurementsData = measurements // Keep reference for useMemo above

  // Handle scroll
  useEffect(() => {
    const element = scrollRef.current
    if (!element) return

    const handleScroll = () => {
      setScrollOffset(element.scrollTop)
      setIsScrolling(true)

      // Clear existing timeout
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current)
      }

      // Set new timeout to mark scrolling as finished
      scrollTimeoutRef.current = setTimeout(() => {
        setIsScrolling(false)
      }, 150)
    }

    // Use passive listener for better performance
    element.addEventListener('scroll', handleScroll, { passive: true })
    
    // Initial measurement
    setContainerHeight(element.clientHeight)
    setScrollOffset(element.scrollTop)

    // Resize observer for container height changes
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height)
      }
    })
    resizeObserver.observe(element)

    return () => {
      element.removeEventListener('scroll', handleScroll)
      resizeObserver.disconnect()
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current)
      }
    }
  }, [])

  // Scroll to index
  const scrollToIndex = useCallback((index: number, behavior: ScrollBehavior = 'smooth') => {
    const element = scrollRef.current
    if (!element) return

    const targetOffset = measurementsData.measurements[index]?.offset ?? 0
    element.scrollTo({ top: targetOffset, behavior })
  }, [measurementsData])

  // Scroll to offset
  const scrollToOffset = useCallback((offset: number, behavior: ScrollBehavior = 'smooth') => {
    const element = scrollRef.current
    if (!element) return

    element.scrollTo({ top: offset, behavior })
  }, [])

  return {
    virtualItems,
    totalHeight: measurements.totalHeight,
    scrollRef,
    scrollToIndex,
    scrollToOffset,
    isScrolling,
  }
}

/**
 * useInfiniteScroll - Infinite scrolling with intersection observer
 * 
 * @example
 * const { ref, hasMore, isLoading } = useInfiniteScroll({
 *   onLoadMore: fetchMore,
 *   hasMore: page < totalPages
 * })
 */
interface InfiniteScrollOptions {
  onLoadMore: () => Promise<void> | void
  hasMore: boolean
  threshold?: number
  rootMargin?: string
}

interface InfiniteScrollResult {
  ref: React.RefObject<HTMLDivElement>
  isLoading: boolean
}

export function useInfiniteScroll(options: InfiniteScrollOptions): InfiniteScrollResult {
  const { onLoadMore, hasMore, threshold = 0, rootMargin = '100px' } = options
  const ref = useRef<HTMLDivElement>(null)
  const [isLoading, setIsLoading] = useState(false)
  const isLoadingRef = useRef(false)

  useEffect(() => {
    const element = ref.current
    if (!element || !hasMore) return

    const observer = new IntersectionObserver(
      async (entries) => {
        const [entry] = entries
        if (entry.isIntersecting && !isLoadingRef.current && hasMore) {
          isLoadingRef.current = true
          setIsLoading(true)
          
          try {
            await onLoadMore()
          } finally {
            isLoadingRef.current = false
            setIsLoading(false)
          }
        }
      },
      { threshold, rootMargin }
    )

    observer.observe(element)

    return () => observer.disconnect()
  }, [onLoadMore, hasMore, threshold, rootMargin])

  return { ref, isLoading }
}

/**
 * useWindowVirtualizer - Virtualize items in window/document scroll
 * Useful for full-page lists
 * 
 * @example
 * const { virtualItems, totalHeight, measureElement } = useWindowVirtualizer({
 *   count: 10000,
 *   estimateSize: () => 50
 * })
 */
interface WindowVirtualizerOptions {
  count: number
  estimateSize: (index: number) => number
  overscan?: number
  scrollPaddingStart?: number
  scrollPaddingEnd?: number
}

interface WindowVirtualizerResult {
  virtualItems: { index: number; offset: number; size: number }[]
  totalHeight: number
  measureElement: (el: HTMLElement | null, index: number) => void
  scrollToIndex: (index: number) => void
}

export function useWindowVirtualizer(
  options: WindowVirtualizerOptions
): WindowVirtualizerResult {
  const {
    count,
    estimateSize,
    overscan = 5,
    scrollPaddingStart = 0,
    scrollPaddingEnd = 0,
  } = options

  const [scrollOffset, setScrollOffset] = useState(0)
  const [windowHeight, setWindowHeight] = useState(0)
  const measuredSizes = useRef<Map<number, number>>(new Map())

  // Calculate range
  const virtualItems = useMemo(() => {
    const items: { index: number; offset: number; size: number }[] = []
    
    if (!windowHeight) return items

    let totalOffset = scrollPaddingStart
    
    for (let i = 0; i < count; i++) {
      const size = measuredSizes.current.get(i) ?? estimateSize(i)
      
      // Check if item is in view (with overscan)
      if (totalOffset + size > scrollOffset - overscan * estimateSize(i) &&
          totalOffset < scrollOffset + windowHeight + overscan * estimateSize(i)) {
        items.push({ index: i, offset: totalOffset, size })
      }
      
      totalOffset += size
    }

    return items
  }, [count, estimateSize, scrollOffset, windowHeight, overscan, scrollPaddingStart])

  // Total height for the container
  const totalHeight = useMemo(() => {
    let height = scrollPaddingStart
    for (let i = 0; i < count; i++) {
      height += measuredSizes.current.get(i) ?? estimateSize(i)
    }
    return height + scrollPaddingEnd
  }, [count, estimateSize, scrollPaddingStart, scrollPaddingEnd])

  // Handle scroll and resize
  useEffect(() => {
    const handleScroll = () => {
      setScrollOffset(window.scrollY)
    }

    const handleResize = () => {
      setWindowHeight(window.innerHeight)
    }

    // Initial values
    handleScroll()
    handleResize()

    window.addEventListener('scroll', handleScroll, { passive: true })
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('scroll', handleScroll)
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  // Measure element callback
  const measureElement = useCallback((el: HTMLElement | null, index: number) => {
    if (el) {
      const size = el.getBoundingClientRect().height
      measuredSizes.current.set(index, size)
    }
  }, [])

  // Scroll to index
  const scrollToIndex = useCallback((index: number) => {
    let offset = scrollPaddingStart
    for (let i = 0; i < index && i < count; i++) {
      offset += measuredSizes.current.get(i) ?? estimateSize(i)
    }
    window.scrollTo({ top: offset, behavior: 'smooth' })
  }, [count, estimateSize, scrollPaddingStart])

  return {
    virtualItems,
    totalHeight,
    measureElement,
    scrollToIndex,
  }
}
