'use client';

import dynamic from 'next/dynamic';

// Dynamically import Map component with no SSR (mapbox-gl requires window)
const Map = dynamic(() => import('@/components/Map'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-screen flex items-center justify-center bg-gray-100">
      <p className="text-gray-500">Loading map...</p>
    </div>
  ),
});

export default function Home() {
  return (
    <main className="w-full h-screen">
      <Map />
    </main>
  );
}
