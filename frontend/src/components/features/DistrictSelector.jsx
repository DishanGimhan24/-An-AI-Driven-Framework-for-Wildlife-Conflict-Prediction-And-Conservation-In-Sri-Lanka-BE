import { DISTRICTS } from '../../utils/constants';
import Select from '../common/Select';

export default function DistrictSelector({ value, onChange, label = "Select District", required = false }) {
  const options = DISTRICTS.map(district => ({
    value: district,
    label: district
  }));

  

  return (
    <Select
      label={label}
      value={value}
      onChange={onChange}
      options={options}
      placeholder="Choose a district"
      required={required}
    />
  );
}