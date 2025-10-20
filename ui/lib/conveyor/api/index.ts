import { electronAPI } from '@electron-toolkit/preload'
import { AppApi } from './app-api'
import { WindowApi } from './window-api'
import { BackendApi } from './backend-api'
import { OmniApi } from './omni-api'

export const conveyor = {
  app: new AppApi(electronAPI),
  window: new WindowApi(electronAPI),
  backend: new BackendApi(electronAPI),
  omni: new OmniApi(electronAPI),
}

export type ConveyorApi = typeof conveyor
