import { Minus, Square, X } from 'lucide-react'

export function CustomTitlebar() {
  const handleMinimize = () => {
    // @ts-expect-error - electron API injected by preload
    window.electron?.minimizeWindow()
  }

  const handleMaximize = () => {
    // @ts-expect-error - electron API injected by preload
    window.electron?.maximizeWindow()
  }

  const handleClose = () => {
    // @ts-expect-error - electron API injected by preload
    window.electron?.closeWindow()
  }

  return (
    <div className="h-8 bg-zinc-950 border-b border-zinc-800 flex items-center justify-between px-4 select-none drag-region">
      <div className="flex items-center gap-2">
        <img
          src="res://icons/omni-logo-light.png"
          alt="Omni"
          className="h-5 w-auto object-contain"
        />
        <span className="text-sm text-zinc-400">Automagik Omni</span>
      </div>

      <div className="flex items-center gap-1 no-drag">
        <button
          onClick={handleMinimize}
          className="h-8 w-10 flex items-center justify-center hover:bg-zinc-800 transition-colors"
          title="Minimize"
        >
          <Minus className="h-4 w-4 text-zinc-400" />
        </button>
        <button
          onClick={handleMaximize}
          className="h-8 w-10 flex items-center justify-center hover:bg-zinc-800 transition-colors"
          title="Maximize"
        >
          <Square className="h-3.5 w-3.5 text-zinc-400" />
        </button>
        <button
          onClick={handleClose}
          className="h-8 w-10 flex items-center justify-center hover:bg-red-600 transition-colors"
          title="Close"
        >
          <X className="h-4 w-4 text-zinc-400 hover:text-white" />
        </button>
      </div>
    </div>
  )
}
