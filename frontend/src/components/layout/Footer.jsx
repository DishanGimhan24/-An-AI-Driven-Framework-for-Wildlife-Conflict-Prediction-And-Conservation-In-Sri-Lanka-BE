export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-gray-800 text-white py-6 mt-auto">
      <div className="container mx-auto px-4">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="text-center md:text-left mb-4 md:mb-0">
            <p className="text-sm">© {currentYear} ELESAFE - Wildlife Conflict Prediction System</p>
            <p className="text-xs text-gray-400 mt-1">Protecting Communities & Wildlife in Sri Lanka</p>
          </div>
          <div className="flex space-x-6 text-sm">
            <a href="#" className="hover:text-green-400 transition-colors">About</a>
            <a href="#" className="hover:text-green-400 transition-colors">Help</a>
            <a href="#" className="hover:text-green-400 transition-colors">Contact</a>
          </div>
        </div>
      </div>
    </footer>
  );
}