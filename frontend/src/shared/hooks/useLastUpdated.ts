import { useState, useEffect } from 'react'

/**
 * Hook to track and display "last updated" timestamp
 * 
 * Returns a formatted string like "Just now", "30s ago", "2m ago"
 */
export function useLastUpdated(timestamp: number | null): string {
  const [displayText, setDisplayText] = useState<string>('Never')

  useEffect(() => {
    if (!timestamp) {
      setDisplayText('Never')
      return
    }

    const updateDisplay = () => {
      const now = Date.now()
      const diff = now - timestamp
      const seconds = Math.floor(diff / 1000)

      if (seconds < 5) {
        setDisplayText('Just now')
      } else if (seconds < 60) {
        setDisplayText(`${seconds}s ago`)
      } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60)
        setDisplayText(`${minutes}m ago`)
      } else {
        const hours = Math.floor(seconds / 3600)
        setDisplayText(`${hours}h ago`)
      }
    }

    // Update immediately
    updateDisplay()

    // Update every 5 seconds
    const interval = setInterval(updateDisplay, 5000)

    return () => clearInterval(interval)
  }, [timestamp])

  return displayText
}

/**
 * Hook to manage last updated timestamp
 * 
 * Returns [timestamp, updateTimestamp]
 */
export function useLastUpdatedTimestamp(): [number | null, () => void] {
  const [timestamp, setTimestamp] = useState<number | null>(null)

  const updateTimestamp = () => {
    setTimestamp(Date.now())
  }

  return [timestamp, updateTimestamp]
}
