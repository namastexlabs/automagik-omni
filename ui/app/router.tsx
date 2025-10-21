import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { MainLayout } from './layouts/MainLayout'
import Dashboard from './pages/Dashboard'
import Instances from './pages/Instances'
import AccessRules from './pages/AccessRules'
import Messages from './pages/Messages'
import Contacts from './pages/Contacts'
import Chats from './pages/Chats'
import Traces from './pages/Traces'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'instances', element: <Instances /> },
      { path: 'access-rules', element: <AccessRules /> },
      { path: 'messages', element: <Messages /> },
      { path: 'contacts', element: <Contacts /> },
      { path: 'chats', element: <Chats /> },
      { path: 'traces', element: <Traces /> }
    ]
  }
])

export default function Router() {
  return <RouterProvider router={router} />
}
