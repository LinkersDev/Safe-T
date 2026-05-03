import { AppBootstrap } from './app/bootstrap/AppBootstrap'
import { AppProviders } from './app/providers/AppProviders'

function App() {
  return (
    <AppProviders>
      <AppBootstrap />
    </AppProviders>
  )
}

export default App
