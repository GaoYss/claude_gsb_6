import { createResourceApi } from './client'
import http from './client'

export const hazardTreeApi = {
  ...createResourceApi('hazard-trees'),
  changeStatus: (id, payload) => http.patch(`/hazard-trees/${id}/status`, payload),
  generateTask: (id, payload) => http.post(`/hazard-trees/${id}/generate-task`, payload ?? {}),
  addReinspection: (id, payload) => http.post(`/hazard-trees/${id}/reinspections`, payload),
}
