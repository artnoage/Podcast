import React from 'react';

const LoadingSpinner = () => (
  <div className="flex justify-center items-center">
    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-200"></div>
    <span className="ml-2">Creating podcasts...</span>
  </div>
);

export default LoadingSpinner;
