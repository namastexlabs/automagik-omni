import { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

/**
 * ForgeInspector (AutomagikForgeWebCompanion)
 *
 * This component handles communication with the parent Automagik Forge window
 * when the UI is embedded in an iframe. It enables:
 * - Automatic API key injection from Forge
 * - Navigation synchronization
 * - State monitoring and reporting
 */
export function ForgeInspector() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isInIframe, setIsInIframe] = useState(false);
  const [forgeConnected, setForgeConnected] = useState(false);

  useEffect(() => {
    // Detect if we're in an iframe
    const inIframe = window.self !== window.top;
    setIsInIframe(inIframe);

    if (!inIframe) {
      console.log('[ForgeInspector] Not in iframe, skipping initialization');
      return;
    }

    console.log('[ForgeInspector] Initializing in iframe mode');

    // Listen for messages from parent Forge window
    const handleMessage = (event: MessageEvent) => {
      console.log('[ForgeInspector] Received message:', event.data);

      // Validate message origin if needed
      // if (event.origin !== expectedOrigin) return;

      const { type, payload } = event.data;

      switch (type) {
        case 'FORGE_INIT':
          console.log('[ForgeInspector] Forge connected');
          setForgeConnected(true);
          // Send ready acknowledgment
          window.parent.postMessage({ type: 'UI_READY' }, '*');
          break;

        case 'INJECT_API_KEY':
          console.log('[ForgeInspector] Received API key from Forge');
          if (payload?.apiKey) {
            localStorage.setItem('omni_api_key', payload.apiKey);
            // Trigger navigation to dashboard if on login page
            if (location.pathname === '/login') {
              navigate('/dashboard', { replace: true });
            }
          }
          break;

        case 'NAVIGATE':
          console.log('[ForgeInspector] Navigation request:', payload?.path);
          if (payload?.path) {
            navigate(payload.path, { replace: true });
          }
          break;

        default:
          console.log('[ForgeInspector] Unknown message type:', type);
      }
    };

    window.addEventListener('message', handleMessage);

    // Announce presence to parent
    window.parent.postMessage({ type: 'UI_LOADED' }, '*');

    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, [navigate, location.pathname]);

  // Report navigation changes to Forge
  useEffect(() => {
    if (!isInIframe || !forgeConnected) return;

    // Report navigation to parent
    window.parent.postMessage({
      type: 'NAVIGATION_CHANGED',
      payload: { path: location.pathname },
    }, '*');
  }, [isInIframe, forgeConnected, location.pathname]);

  // This component doesn't render anything visible
  return null;
}
