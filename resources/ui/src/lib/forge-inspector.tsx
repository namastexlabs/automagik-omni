import { useEffect, useState } from 'react';

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
            if (window.location.pathname === '/login') {
              window.location.href = '/dashboard';
            }
          }
          break;

        case 'NAVIGATE':
          console.log('[ForgeInspector] Navigation request:', payload?.path);
          if (payload?.path) {
            window.location.href = payload.path;
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
  }, []);

  // Report navigation changes to Forge
  useEffect(() => {
    if (!isInIframe || !forgeConnected) return;

    const reportNavigation = () => {
      window.parent.postMessage({
        type: 'NAVIGATION_CHANGED',
        payload: { path: window.location.pathname },
      }, '*');
    };

    // Report initial navigation
    reportNavigation();

    // Listen for popstate (back/forward navigation)
    window.addEventListener('popstate', reportNavigation);

    return () => {
      window.removeEventListener('popstate', reportNavigation);
    };
  }, [isInIframe, forgeConnected]);

  // This component doesn't render anything visible
  return null;
}
