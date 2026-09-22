FROM python:3.12-slim
RUN pip install --no-cache-dir numpy==2.2.6 scipy==1.15.3 matplotlib==3.10.3 pandas==2.3.1 nbformat nbconvert ipykernel jupyter_client mealpy
WORKDIR /work
CMD ["python", "-c", "print('qi-sched image ready')"]
