import { Navigate, Route, Routes } from 'react-router-dom';
import NavBar from './components/NavBar';
import DataPage from './routes/DataPage';
import TrainPage from './routes/TrainPage';

function App() {
  return (
    <div className="min-vh-100 bg-light">
      <NavBar />
      <main className="container py-4">
        <Routes>
          <Route path="/" element={<Navigate to="/data" replace />} />
          <Route path="/data" element={<DataPage />} />
          <Route path="/train" element={<TrainPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
