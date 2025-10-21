type ConveyorKey = keyof Window['conveyor']

/**
 * Use the conveyor for inter-process communication
 *
 * @param key - The key of the conveyor object to use
 * @returns The conveyor object or the keyed object
 */
export const useConveyor = <T extends ConveyorKey | undefined = undefined>(
  key?: T
): T extends ConveyorKey ? Window['conveyor'][T] : Window['conveyor'] => {
  // Safety check: return empty object if not in Electron context
  if (typeof window === 'undefined' || !window.conveyor) {
    console.warn('Conveyor API not available - not running in Electron context')
    return {} as any
  }

  const conveyor = window.conveyor

  if (key) {
    return conveyor[key] as any
  }

  return conveyor as any
}
