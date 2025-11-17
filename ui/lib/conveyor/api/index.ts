import { electronAPI } from '@electron-toolkit/preload'
import { AppApi } from './app-api'
import { WindowApi } from './window-api'
import { BackendApi } from './backend-api'
import { OmniApi } from './omni-api'
import { EvolutionApi } from './evolution-api'

export const conveyor = {
  app: new AppApi(electronAPI),
  window: new WindowApi(electronAPI),
  backend: new BackendApi(electronAPI),
  omni: new OmniApi(electronAPI),
  evolution: new EvolutionApi(electronAPI),
}

export type ConveyorApi = typeof conveyor
