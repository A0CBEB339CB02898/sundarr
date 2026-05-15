import { useId } from 'react'
import { Field } from '../ui'

export function TextField({
  disabled = false,
  helper,
  label,
  onChange,
  required = false,
  type = 'text',
  value,
}: {
  disabled?: boolean
  helper?: string
  label: string
  onChange: (value: string) => void
  required?: boolean
  type?: string
  value: string
}) {
  const id = useId()

  return (
    <Field label={label} helper={helper} htmlFor={id}>
      <input id={id} disabled={disabled} onChange={(event) => onChange(event.target.value)} required={required} type={type} value={value} />
    </Field>
  )
}
