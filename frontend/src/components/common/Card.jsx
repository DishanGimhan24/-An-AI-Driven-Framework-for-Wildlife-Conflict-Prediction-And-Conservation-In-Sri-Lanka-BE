export default function Card({ children, title, className = '', padding = 'p-6', shadow = 'shadow-md' }) {
  return (
    <div className={`bg-white rounded-lg ${shadow} ${padding} ${className}`}>
      {title && <h3 className="text-lg font-semibold text-gray-800 mb-4">{title}</h3>}
      {children}
    </div>
  );
}