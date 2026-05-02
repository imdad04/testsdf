import { Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import Product from './pages/Product';
import Orders from './pages/Orders';
import Order from './pages/Order';

export default function App() {
  return (
    <div className="max-w-md mx-auto min-h-screen pb-24">
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/product/:id" element={<Product />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/orders/:id" element={<Order />} />
      </Routes>
    </div>
  );
}
