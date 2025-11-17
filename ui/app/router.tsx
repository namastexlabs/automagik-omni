import { createHashRouter, RouterProvider } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import { MainLayout } from './layouts/MainLayout'
import Dashboard from './pages/Dashboard'
import Instances from './pages/Instances'
import AccessRules from './pages/AccessRules'
import Messages from './pages/Messages'
import Contacts from './pages/Contacts'
import Chats from './pages/Chats'
import Traces from './pages/Traces'

// Use HashRouter for Electron compatibility (file:// protocol support)
export const router = createHashRouter([
  {
    path: '/',
    element: <MainLayout />,
    errorElement: <ErrorBoundary />,
    children: [
      { index: true, element: <Dashboard />, errorElement: <ErrorBoundary /> },
      { path: 'instances', element: <Instances />, errorElement: <ErrorBoundary /> },
      { path: 'access-rules', element: <AccessRules />, errorElement: <ErrorBoundary /> },
      { path: 'messages', element: <Messages />, errorElement: <ErrorBoundary /> },
      { path: 'contacts', element: <Contacts />, errorElement: <ErrorBoundary /> },
      { path: 'chats', element: <Chats />, errorElement: <ErrorBoundary /> },
      { path: 'traces', element: <Traces />, errorElement: <ErrorBoundary /> }
    ]
  }
])

export default function Router() {
  return <RouterProvider router={router} />
}
