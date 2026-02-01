// Performance hooks
export {
  useDebounce,
  useDebounceCallback,
  useThrottle,
  useMemoized,
  useOptimizedQuery,
  useIntersectionObserver,
  useRenderCount,
  useWhyDidYouUpdate,
} from './usePerformance'

// Virtual list hooks
export {
  useVirtualList,
  useInfiniteScroll,
  useWindowVirtualizer,
} from './useVirtualList'

// Keyboard shortcuts
export {
  useKeyboardShortcut,
  useKeyboardShortcuts,
  useFocusScope,
  parseShortcut,
  formatShortcut,
  getModKey,
  COMMON_SHORTCUTS,
} from './useKeyboardShortcuts'

// Accessibility hooks
export {
  useFocusTrap,
  useAriaLive,
  useReducedMotion,
  useHighContrast,
  useColorScheme,
  useClickOutside,
  useAnnounceLoading,
  usePageTitle,
  useUniqueId,
  useAriaIds,
  SkipLink,
  VisuallyHidden,
  KEY_CODES,
} from './useA11y'
