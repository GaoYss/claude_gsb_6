import { createResourceApi } from './client'
import http from './client'

export const hazardousTreeApi = {
  ...createResourceApi('hazardous-trees'),
  registerDisposal: (id, payload) => http.patch(`/hazardous-trees/${id}/disposal`, payload),
  registerRecheck: (id, payload) => http.patch(`/hazardous-trees/${id}/recheck`, payload),
}
