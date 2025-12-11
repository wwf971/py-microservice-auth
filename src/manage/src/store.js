import { atom } from 'jotai'

// Individual atoms for each server
export const auxServerAtom = atom({
  name: 'aux',
  port: 16203,
  isAlive: null,  // null = unknown, true/false = status
  lastChecked: null,
})

export const grpcServerAtom = atom({
  name: 'grpc',
  port: 16200,
  isAlive: null,
  lastChecked: null,
})

export const httpServerAtom = atom({
  name: 'http',
  port: 16201,
  isAlive: null,
  lastChecked: null,
})

// Object gathering all server atoms (not an atom itself)
export const serverState = {
  aux: auxServerAtom,
  grpc: grpcServerAtom,
  http: httpServerAtom,
}

