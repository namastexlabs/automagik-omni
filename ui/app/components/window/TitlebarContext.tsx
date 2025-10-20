import { createContext, useContext, useState } from 'react'

interface TitlebarContextProps {
  activeMenuIndex: number | null
  menusVisible: boolean
  setActiveMenuIndex: (index: number | null) => void
  setMenusVisible: (visible: boolean) => void
  closeActiveMenu: () => void
}

const TitlebarContext = createContext<TitlebarContextProps | undefined>(undefined)

export const TitlebarContextProvider = ({ children }: { children: React.ReactNode }) => {
  const [activeMenuIndex, setActiveMenuIndex] = useState<number | null>(null)
  const [menusVisible, setMenusVisible] = useState(false)
  const closeActiveMenu = () => setActiveMenuIndex(null)

  return (
    <TitlebarContext.Provider
      value={{ activeMenuIndex, menusVisible, setActiveMenuIndex, setMenusVisible, closeActiveMenu }}
    >
      {children}
    </TitlebarContext.Provider>
  )
}

export const useTitlebarContext = () => {
  const context = useContext(TitlebarContext)
  if (!context) {
    throw new Error('useTitlebarContext must be used within a TitlebarContextProvider')
  }
  return context
}
